# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.gtk contains all GTK backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
'''

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, GObject, GdkPixbuf, GLib
import cairo
import threading
import os
import logging
from ...yui_common import *


class YAlignmentGtk(YSingleChildContainerWidget):
    """
    GTK4 implementation of YAlignment.

    - Uses a Gtk.Grid as a lightweight container that expands to provide space
        so child halign/valign can take effect. Gtk.Grid honors child halign/valign
        within its allocation, which matches YAlignment.h semantics.
    - Applies halign/valign hints to the child's backend widget.
    - Defers attaching the child if its backend is not yet created (GLib.idle_add).
    - Supports an optional repeating background pixbuf painted in the draw signal.
    """
    def __init__(self, parent=None, horAlign: YAlignmentType=YAlignmentType.YAlignUnchanged, vertAlign: YAlignmentType=YAlignmentType.YAlignUnchanged):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        self._halign_spec = horAlign
        self._valign_spec = vertAlign
        self._background_pixbuf = None
        self._signal_id = None
        self._backend_widget = None
        # get a reference to the single row container
        self._row = []
        # schedule guard for deferred attach
        self._attach_scheduled = False
        # Track if we've already attached a child
        self._child_attached = False

    def widgetClass(self):
        return "YAlignment"

    def _to_gtk_halign(self):
        """Convert Horizontal YAlignmentType to Gtk.Align or Gtk.Align.CENTER."""        
        if self._halign_spec:
            if self._halign_spec == YAlignmentType.YAlignBegin:
                return Gtk.Align.START
            if self._halign_spec == YAlignmentType.YAlignCenter:
                return Gtk.Align.CENTER
            if self._halign_spec == YAlignmentType.YAlignEnd:
                return Gtk.Align.END
        #default
        return Gtk.Align.CENTER
    
    def _to_gtk_valign(self):
        """Convert Vertical YAlignmentType to Gtk.Align or Gtk.Align.CENTER."""        
        if self._valign_spec:
            if self._valign_spec == YAlignmentType.YAlignBegin:
                return Gtk.Align.START
            if self._valign_spec == YAlignmentType.YAlignCenter:
                return Gtk.Align.CENTER
            if self._valign_spec == YAlignmentType.YAlignEnd:
                return Gtk.Align.END
        #default
        return Gtk.Align.CENTER

    #def stretchable(self, dim):
    #    """Report whether this alignment should expand in given dimension.
    #
    #    Parents (HBox/VBox) use this to distribute space.
    #    """
    #    try:
    #        if dim == YUIDimension.YD_HORIZ:
    #            align = self._to_gtk_halign()
    #            return align in (Gtk.Align.CENTER, Gtk.Align.END) #TODO: verify
    #        if dim == YUIDimension.YD_VERT:
    #            align = self._to_gtk_valign()
    #            return align == Gtk.Align.CENTER #TODO: verify
    #    except Exception:
    #        pass
    #    return False

    def stretchable(self, dim: YUIDimension):
        """Stretchability semantics consistent with YAlignment.h:
        - In the aligned dimension (Begin/Center/End), the alignment container is stretchable
          so there is space for alignment to take effect.
        - In the unchanged dimension, reflect the child's stretchability or layout weight.
        """
        try:
            if dim == YUIDimension.YD_HORIZ:
                if self._halign_spec is not None and self._halign_spec != YAlignmentType.YAlignUnchanged:
                    return True
            if dim == YUIDimension.YD_VERT:
                if self._valign_spec is not None and self._valign_spec != YAlignmentType.YAlignUnchanged:
                    return True
        except Exception:
            pass

        child = self.child()
        if child:
            try:
                return bool(child.stretchable(dim) or child.weight(dim))
            except Exception:
                return False
        return False

    def setBackgroundPixmap(self, filename):
        """Set a repeating background pixbuf and connect draw handler."""
        # disconnect previous handler
        if self._signal_id and self._backend_widget:
            try:
                self._backend_widget.disconnect(self._signal_id)
            except Exception:
                pass
            self._signal_id = None

        # release previous pixbuf if present
        self._background_pixbuf = None

        if filename:
            try:
                self._background_pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
                if self._backend_widget:
                    self._signal_id = self._backend_widget.connect("draw", self._on_draw)
                    self._backend_widget.queue_draw()  # Trigger redraw
            except Exception as e:
                self._logger.error("Failed to load background image: %s", e, exc_info=True)
                self._background_pixbuf = None

    def _on_draw(self, widget, cr):
        """Draw callback that tiles the background pixbuf."""
        if not self._background_pixbuf:
            return False
        try:
            # Get actual allocation
            width = widget.get_allocated_width()
            height = widget.get_allocated_height()
            
            Gdk.cairo_set_source_pixbuf(cr, self._background_pixbuf, 0, 0)
            # set repeat
            pat = cr.get_source()
            pat.set_extend(cairo.Extend.REPEAT)
            cr.rectangle(0, 0, width, height)
            cr.fill()
        except Exception as e:
            self._logger.error("Error drawing background: %s", e, exc_info=True)
        return False

    def addChild(self, child):
        """Keep base behavior and ensure we attempt to attach child's backend."""
        super().addChild(child)
        self._child_attached = False
        self._schedule_attach_child()

    def _schedule_attach_child(self):
        """Schedule a single idle callback to attach child backend later."""
        if self._attach_scheduled or self._child_attached:
            return
        self._logger.debug("Scheduling child attach in idle")
        self._attach_scheduled = True

        def _idle_cb():
            self._attach_scheduled = False
            try:
                self._ensure_child_attached()
            except Exception as e:
                self._logger.error("Error attaching child: %s", e, exc_info=True)
            return False

        try:
            GLib.idle_add(_idle_cb)
        except Exception:
            # fallback: call synchronously if idle_add not available
            _idle_cb()

    def _ensure_child_attached(self):
        """Attach child's backend to our container using a 3x3 grid built
        from a vertical Gtk.Box with three Gtk.CenterBox rows. Position the
        child in the appropriate row and slot according to halign/valign.
        """
        if self._backend_widget is None:
            self._create_backend_widget()
            return

        # choose child reference
        child = self.child()
        if child is None:
            return

        # get child's backend widget
        try:
            cw = child.get_backend_widget()
        except Exception:
            cw = None

        if cw is None:
            # child backend not yet ready; schedule again
            if not self._child_attached:
                self._logger.debug("Child %s %s backend not ready; deferring attach", child.widgetClass(), child.debugLabel())
                self._schedule_attach_child()
            return

        # convert specs -> Gtk.Align
        hal = self._to_gtk_halign()
        val = self._to_gtk_valign()

        try:

            # Determine row index based on vertical alignment
            row_index = 0 if val == Gtk.Align.START else 2 if val == Gtk.Align.END else 1  # center default
            target_cb = self._row[row_index]

            # Place child in start/center/end based on horizontal alignment
            # Default to center if unspecified
            try:
                # Clear any existing widgets in the target centerbox slots
                target_cb.set_start_widget(None)
                target_cb.set_center_widget(None)
                target_cb.set_end_widget(None)
            except Exception:
                pass
            cw.set_halign(hal)
            cw.set_valign(val)

            if hal == Gtk.Align.START:
                target_cb.set_start_widget(cw)
            elif hal == Gtk.Align.END:
                target_cb.set_end_widget(cw)
            else:
                target_cb.set_center_widget(cw)

            self._backend_widget.set_halign(hal)
            self._backend_widget.set_valign(val)
            #self._backend_widget.set_hexpand(True)
            #self._backend_widget.set_vexpand(True)
            self._child_attached = True

            col_index = 0 if hal == Gtk.Align.START else 2 if hal == Gtk.Align.END else 1  # center default
            self._logger.debug("Successfully attached child %s %s [%d,%d]", child.widgetClass(), child.label(), row_index, col_index)
        except Exception as e:
            self._logger.error("Error building CenterBox layout: %s", e, exc_info=True)

    def _create_backend_widget(self):
        """Create a container for the 3x3 alignment layout.

        Use a simple Gtk.Box as root container; actual 3x3 is built on attach.
        """
        try:
            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            root.set_hexpand(True)
            root.set_vexpand(True)
            root.set_halign(Gtk.Align.FILL)
            root.set_valign(Gtk.Align.FILL)
            
            for _ in range(3):
                cb = Gtk.CenterBox()
                cb.set_hexpand(True)
                cb.set_vexpand(True)
                cb.set_halign(Gtk.Align.FILL)
                cb.set_valign(Gtk.Align.FILL)
                cb.set_margin_start(0)
                cb.set_margin_end(0)
                self._row.append(cb)
                root.append(cb)
            
            for cb in self._row:
                cb.set_vexpand(True)
            

        except Exception as e:
            self._logger.error("Error creating backend widget: %s", e, exc_info=True)
            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self._backend_widget = root
        self._backend_widget.set_sensitive(self._enabled)

        # Connect draw handler if we have a background pixbuf
        if self._background_pixbuf and not self._signal_id:
            try:
                self._signal_id = self._backend_widget.connect("draw", self._on_draw)
            except Exception as e:
                self._logger.error("Error connecting draw signal: %s", e, exc_info=True)
                self._signal_id = None

        # Mark that backend is ready and attempt to attach child
        self._ensure_child_attached()
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def get_backend_widget(self):
        """Return the backend GTK widget."""
        if self._backend_widget is None:
            self._create_backend_widget()
        return self._backend_widget

    def setSize(self, width, height):
        """Set size of the alignment widget."""
        if self._backend_widget:
            if width > 0 and height > 0:
                self._backend_widget.set_size_request(width, height)
            else:
                self._backend_widget.set_size_request(-1, -1)

    def setEnabled(self, enabled):
        """Set widget enabled state."""
        if self._backend_widget:
            self._backend_widget.set_sensitive(enabled)
        super().setEnabled(enabled)

    def setVisible(self, visible):
        """Set widget visibility."""
        if self._backend_widget:
            try:
                self._backend_widget.set_visible(visible)
            except Exception:
                pass
        super().setVisible(visible)

    def _set_backend_enabled(self, enabled):
        """Enable/disable the alignment container and its child (if any)."""
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass
        # propagate to logical child so child's backend updates too
        try:
            child = self.child()
            if child is not None:
                child.setEnabled(enabled)
        except Exception:
            pass
