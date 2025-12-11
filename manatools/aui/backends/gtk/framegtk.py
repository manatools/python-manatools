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


class YFrameGtk(YSingleChildContainerWidget):
    """
    GTK backend implementation of YFrame.

    - Uses Gtk.Frame (when available) to present a labeled framed container.
    - Internally places a Gtk.Box inside the frame to host the single child.
    - Honors child's stretchability: the frame reports stretchable when its child is stretchable
      so parent layouts can allocate extra space.
    - Provides simple property support for 'label'.
    """
    def __init__(self, parent=None, label: str = ""):
        super().__init__(parent)
        self._label = label or ""
        self._backend_widget = None
        self._content_box = None

    def widgetClass(self):
        return "YFrame"

    def label(self):
        return self._label

    def setLabel(self, new_label: str):
        """Set the frame label and update backend if created."""
        try:
            self._label = new_label or ""
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    # Gtk.Frame in GTK4 supports set_label() in some bindings, else use a child label
                    if hasattr(self._backend_widget, "set_label"):
                        self._backend_widget.set_label(self._label)
                    else:
                        # fallback: if we created a dedicated label child, update it
                        if getattr(self, "_label_widget", None) is not None:
                            try:
                                self._label_widget.set_text(self._label)
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            pass

    def stretchable(self, dim: YUIDimension):
        """
        Report stretchability in a dimension.

        The frame is stretchable when its child is stretchable or has a layout weight.
        """
        try:
            child = self.child()
            if child is None:
                return False
            try:
                if bool(child.stretchable(dim)):
                    return True
            except Exception:
                pass
            try:
                if bool(child.weight(dim)):
                    return True
            except Exception:
                pass
        except Exception:
            pass
        return False

    def _attach_child_backend(self):
        """Attach the child's backend widget into the frame's content box."""
        try:
            if self._backend_widget is None:
                return
            if self._content_box is None:
                return
            child = self.child()
            if child is None:
                return
            try:
                cw = child.get_backend_widget()
            except Exception:
                cw = None
            if cw is None:
                return

            # Remove existing content children (defensive)
            try:
                while True:
                    first = self._content_box.get_first_child()
                    if first is None:
                        break
                    try:
                        self._content_box.remove(first)
                    except Exception:
                        break
            except Exception:
                pass

            # Append child widget into content box
            try:
                self._content_box.append(cw)
            except Exception:
                try:
                    self._content_box.add(cw)
                except Exception:
                    pass

            # Ensure expansion hints propagate from child
            try:
                if child.stretchable(YUIDimension.YD_VERT):
                    if hasattr(cw, "set_vexpand"):
                        cw.set_vexpand(True)
                    if hasattr(cw, "set_valign"):
                        cw.set_valign(Gtk.Align.FILL)
                else:
                    if hasattr(cw, "set_vexpand"):
                        cw.set_vexpand(False)
                    if hasattr(cw, "set_valign"):
                        cw.set_valign(Gtk.Align.START)
                if child.stretchable(YUIDimension.YD_HORIZ):
                    if hasattr(cw, "set_hexpand"):
                        cw.set_hexpand(True)
                    if hasattr(cw, "set_halign"):
                        cw.set_halign(Gtk.Align.FILL)
                else:
                    if hasattr(cw, "set_hexpand"):
                        cw.set_hexpand(False)
                    if hasattr(cw, "set_halign"):
                        cw.set_halign(Gtk.Align.START)
            except Exception:
                pass
        except Exception:
            pass

    def addChild(self, child):
        """Add logical child and attach backend if possible."""
        super().addChild(child)
        # best-effort fallback
        self._attach_child_backend()

    def _create_backend_widget(self):
        """
        Create a Gtk.Frame + inner box to host the single child.
        Fall back to a bordered Gtk.Box when Gtk.Frame or set_label is not available.
        """
        try:
            # Try to create a Gtk.Frame with a label if supported
            try:
                frame = Gtk.Frame()
                # set label if API supports it
                if hasattr(frame, "set_label"):
                    frame.set_label(self._label)
                    self._label_widget = None
                else:
                    # create a label widget and set as label using set_label_widget if supported
                    lbl = Gtk.Label(label=self._label)
                    self._label_widget = lbl
                    if hasattr(frame, "set_label_widget"):
                        frame.set_label_widget(lbl)
                # Create inner content box
                content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                content.set_hexpand(True)
                content.set_vexpand(True)
                # Append content inside frame. In GTK4 a Frame can have a single child.
                try:
                    frame.set_child(content)
                except Exception:
                    try:
                        # fallback: some bindings use add()
                        frame.add(content)
                    except Exception:
                        pass
                self._backend_widget = frame
                self._content_box = content
                self._backend_widget.set_sensitive(self._enabled)
                # attach existing child if any
                try:
                    if self.hasChildren():
                        self._attach_child_backend()
                except Exception:
                    pass
                return
            except Exception:
                # fallback to a boxed container with a visible border using CSS if Frame creation fails
                pass

            # Fallback container: vertical box with a top label and a framed-like border (best-effort)
            container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            try:
                lbl = Gtk.Label(label=self._label)
                lbl.set_xalign(0.0)
                container.append(lbl)
                # content area
                content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                content.set_hexpand(True)
                content.set_vexpand(True)
                container.append(content)
                self._label_widget = lbl
                self._backend_widget = container
                self._content_box = content
                if self.hasChildren():
                    try:
                        self._attach_child_backend()
                    except Exception:
                        pass
            except Exception:
                # ultimate fallback: empty widget reference
                self._backend_widget = None
                self._content_box = None
        except Exception:
            self._backend_widget = None
            self._content_box = None

    def _set_backend_enabled(self, enabled):
        """Enable/disable the frame and propagate to child."""
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass
        # propagate to logical child
        try:
            child = self.child()
            if child is not None:
                try:
                    child.setEnabled(enabled)
                except Exception:
                    pass
        except Exception:
            pass

    def setProperty(self, propertyName, val):
        """Handle simple properties; returns True if property handled here."""
        try:
            if propertyName == "label":
                try:
                    self.setLabel(str(val))
                except Exception:
                    pass
                return True
        except Exception:
            pass
        return False

    def getProperty(self, propertyName):
        try:
            if propertyName == "label":
                return self.label()
        except Exception:
            pass
        return None

    def propertySet(self):
        """Return a minimal property set description for introspection."""
        try:
            props = YPropertySet()
            try:
                props.add(YProperty("label", YPropertyType.YStringProperty))
            except Exception:
                pass
            return props
        except Exception:
            return None
