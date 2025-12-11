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
from ...yui_common import *


class YAlignmentGtk(YSingleChildContainerWidget):
    """
    GTK4 implementation of YAlignment.

    - Uses a Gtk.Box as a lightweight container that requests expansion when
      needed so child halign/valign can take effect (matches the small GTK sample).
    - Applies halign/valign hints to the child's backend widget.
    - Defers attaching the child if its backend is not yet created (GLib.idle_add).
    - Supports an optional repeating background pixbuf painted in the draw signal.
    """
    def __init__(self, parent=None, horAlign: YAlignmentType=YAlignmentType.YAlignUnchanged, vertAlign: YAlignmentType=YAlignmentType.YAlignUnchanged):
        super().__init__(parent)
        self._halign_spec = horAlign
        self._valign_spec = vertAlign
        self._background_pixbuf = None
        self._signal_id = None
        self._backend_widget = None
        # schedule guard for deferred attach
        self._attach_scheduled = False
        # Track if we've already attached a child
        self._child_attached = False

    def widgetClass(self):
        return "YAlignment"

    def _to_gtk_halign(self):
        """Convert Horizontal YAlignmentType to Gtk.Align or None."""        
        if self._halign_spec:
            if self._halign_spec == YAlignmentType.YAlignBegin:
                return Gtk.Align.START
            if self._halign_spec == YAlignmentType.YAlignCenter:
                return Gtk.Align.CENTER
            if self._halign_spec == YAlignmentType.YAlignEnd:
                return Gtk.Align.END
        return None
    
    def _to_gtk_valign(self):
        """Convert Vertical YAlignmentType to Gtk.Align or None."""        
        if self._valign_spec:
            if self._valign_spec == YAlignmentType.YAlignBegin:
                return Gtk.Align.START
            if self._valign_spec == YAlignmentType.YAlignCenter:
                return Gtk.Align.CENTER
            if self._valign_spec == YAlignmentType.YAlignEnd:
                return Gtk.Align.END
        return None

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
        ''' Returns the stretchability of the layout box:
          * The layout box is stretchable if the child is stretchable in
          * this dimension or if the child widget has a layout weight in
          * this dimension.
        '''
        if self.child():
            expand = bool(self.child().stretchable(dim))
            weight = bool(self.child().weight(dim))
            if expand or weight:
                return True
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
                print(f"Failed to load background image: {e}")
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
            print(f"Error drawing background: {e}")
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
        self._attach_scheduled = True

        def _idle_cb():
            self._attach_scheduled = False
            try:
                self._ensure_child_attached()
            except Exception as e:
                print(f"Error attaching child: {e}")
            return False

        try:
            GLib.idle_add(_idle_cb)
        except Exception:
            # fallback: call synchronously if idle_add not available
            _idle_cb()

    def _ensure_child_attached(self):
        """Attach child's backend to our container, apply alignment hints."""
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
                self._schedule_attach_child()
            return

        # convert specs -> Gtk.Align
        hal = self._to_gtk_halign()
        val = self._to_gtk_valign()

        # Apply alignment and expansion hints to child
        try:
            # Set horizontal alignment and expansion
            if hasattr(cw, "set_halign"):
                if hal is not None:
                    cw.set_halign(hal)
                else:
                    cw.set_halign(Gtk.Align.FILL)
                
                # Request expansion for alignment to work properly
                cw.set_hexpand(True)
            
            # Set vertical alignment and expansion  
            if hasattr(cw, "set_valign"):
                if val is not None:
                    cw.set_valign(val)
                else:
                    cw.set_valign(Gtk.Align.FILL)
                
                # Request expansion for alignment to work properly
                cw.set_vexpand(True)
                
        except Exception as e:
            print(f"Error setting alignment properties: {e}")

        # If the child widget is already parented to us, nothing to do
        parent_of_cw = None
        try:
            if hasattr(cw, 'get_parent'):
                parent_of_cw = cw.get_parent()
        except Exception:
            parent_of_cw = None

        if parent_of_cw == self._backend_widget:
            self._child_attached = True
            return

        # Remove any existing children from our container
        try:
            # In GTK4, we need to remove all existing children
            while True:
                child_widget = self._backend_widget.get_first_child()
                if child_widget is None:
                    break
                self._backend_widget.remove(child_widget)
        except Exception as e:
            print(f"Error removing existing children: {e}")

        # Append child to our box - this is the critical fix for GTK4
        try:
            self._backend_widget.append(cw)
            self._child_attached = True
            print(f"Successfully attached child {child.widgetClass()} {child.debugLabel()} to alignment container")
        except Exception as e:
            print(f"Error appending child: {e}")
            # Try alternative method for GTK4
            try:
                self._backend_widget.set_child(cw)
                self._child_attached = True
                print(f"Successfully set child {child.widgetClass()} {child.debugLabel()} using set_child()")
            except Exception as e2:
                print(f"Error setting child: {e2}")

    def _create_backend_widget(self):
        """Create a Box container oriented to allow alignment to work.

        In GTK4, we use a simple Box that expands in both directions
        to provide space for the child widget to align within.
        """
        try:
            # Use a box that can expand in both directions
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            
            # Make the box expand to fill available space
            box.set_hexpand(True)
            box.set_vexpand(True)
            
            # Set the box to fill its allocation so child has space to align
            box.set_halign(Gtk.Align.FILL)
            box.set_valign(Gtk.Align.FILL)
            
        except Exception as e:
            print(f"Error creating backend widget: {e}")
            box = Gtk.Box()

        self._backend_widget = box
        self._backend_widget.set_sensitive(self._enabled)

        # Connect draw handler if we have a background pixbuf
        if self._background_pixbuf and not self._signal_id:
            try:
                self._signal_id = box.connect("draw", self._on_draw)
            except Exception as e:
                print(f"Error connecting draw signal: {e}")
                self._signal_id = None

        # Mark that backend is ready and attempt to attach child
        self._ensure_child_attached()

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
