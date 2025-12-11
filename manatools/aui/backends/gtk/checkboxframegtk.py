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

class YCheckBoxFrameGtk(YSingleChildContainerWidget):
    """
    GTK backend for YCheckBoxFrame: a frame with a checkbutton in the title area
    that enables/disables its child. The implementation prefers to place the
    CheckButton into the Frame's label widget (if supported) so the theme draws
    the frame title and border consistently.
    """
    def __init__(self, parent=None, label: str = "", checked: bool = False):
        super().__init__(parent)
        self._label = label or ""
        self._checked = bool(checked)
        self._auto_enable = True
        self._invert_auto = False

        self._backend_widget = None
        self._checkbox = None
        self._content_box = None
        self._label_widget = None

    def widgetClass(self):
        return "YCheckBoxFrame"

    def label(self):
        return self._label

    def setLabel(self, new_label: str):
        try:
            self._label = new_label or ""
            if getattr(self, "_checkbox", None) is not None:
                try:
                    # Gtk.CheckButton uses set_label via property or set_text
                    if hasattr(self._checkbox, "set_label"):
                        self._checkbox.set_label(self._label)
                    elif hasattr(self._checkbox, "set_text"):
                        self._checkbox.set_text(self._label)
                    else:
                        # fallback: recreate label if necessary (best-effort)
                        pass
                except Exception:
                    pass
            # if we used a separate label widget, update it too
            try:
                if getattr(self, "_label_widget", None) is not None:
                    self._label_widget.set_text(self._label)
            except Exception:
                pass
        except Exception:
            pass

    def value(self):
        try:
            if getattr(self, "_checkbox", None) is not None:
                return bool(self._checkbox.get_active())
        except Exception:
            pass
        return bool(self._checked)

    def setValue(self, isChecked: bool):
        try:
            self._checked = bool(isChecked)
            if getattr(self, "_checkbox", None) is not None:
                try:
                    self._checkbox.handler_block_by_func(self._on_toggled)
                except Exception:
                    pass
                try:
                    self._checkbox.set_active(self._checked)
                except Exception:
                    try:
                        self._checkbox.set_active(self._checked)
                    except Exception:
                        pass
                try:
                    self._checkbox.handler_unblock_by_func(self._on_toggled)
                except Exception:
                    pass
            # apply enable/disable to children
            self._apply_children_enablement(self._checked)
        except Exception:
            pass

    def autoEnable(self):
        return bool(self._auto_enable)

    def setAutoEnable(self, autoEnable: bool):
        try:
            self._auto_enable = bool(autoEnable)
            self._apply_children_enablement(self.value())
        except Exception:
            pass

    def invertAutoEnable(self):
        return bool(self._invert_auto)

    def setInvertAutoEnable(self, invert: bool):
        try:
            self._invert_auto = bool(invert)
            self._apply_children_enablement(self.value())
        except Exception:
            pass

    def _create_backend_widget(self):
        """Create Gtk.Frame (or fallback container) and place a CheckButton in the title area."""
        try:
            # Try Gtk.Frame and place a checkbutton as label widget (theme-aware)
            try:
                frame = Gtk.Frame()
                # create inner content box
                content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                try:
                    content.set_hexpand(True)
                    content.set_vexpand(True)
                except Exception:
                    pass

                # Create checkbutton and try to set it as the frame's label widget
                check = Gtk.CheckButton(label=self._label)
                check.set_active(self._checked)
                self._checkbox = check

                # If Gtk.Frame supports set_label_widget use it for themed title
                if hasattr(frame, "set_label_widget"):
                    try:
                        frame.set_label_widget(check)
                    except Exception:
                        # fallback: append check above content
                        pass

                # Attach content inside frame
                try:
                    if hasattr(frame, "set_child"):
                        frame.set_child(content)
                    else:
                        frame.add(content)
                except Exception:
                    try:
                        frame.add(content)
                    except Exception:
                        pass

                self._backend_widget = frame
                self._content_box = content
                self._label_widget = None
            except Exception:
                # Fallback: container with top CheckButton and then content box
                container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                check = Gtk.CheckButton(label=self._label)
                check.set_active(self._checked)
                container.append(check)
                content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                try:
                    content.set_hexpand(True)
                    content.set_vexpand(True)
                except Exception:
                    pass
                container.append(content)
                self._backend_widget = container
                self._checkbox = check
                self._content_box = content
                self._label_widget = None
            self._backend_widget.set_sensitive(self._enabled)

            # Ensure a little top margin between title and content
            try:
                if hasattr(self._content_box, "set_margin_top"):
                    self._content_box.set_margin_top(6)
                else:
                    try:
                        self._content_box.set_spacing(6)
                    except Exception:
                        pass
            except Exception:
                pass

            # Connect toggled handler
            try:
                self._checkbox.connect("toggled", self._on_toggled)
            except Exception:
                try:
                    self._checkbox.connect("toggled", self._on_toggled)
                except Exception:
                    pass

            # attach existing child if any
            try:
                if self.hasChildren():
                    self._attach_child_backend()
            except Exception:
                pass
        except Exception:
            self._backend_widget = None
            self._checkbox = None
            self._content_box = None
            self._label_widget = None

    def _attach_child_backend(self):
        """Attach the logical child backend widget into the content box (clear previous)."""
        if self._content_box is None or self._backend_widget is None:
            return
        try:
            # clear existing children
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
                # fallback for Gtk.Box append/remove API
                try:
                    for child in list(self._content_box.get_children()):
                        try:
                            self._content_box.remove(child)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

        child = self.child()
        if child is None:
            return

        try:
            w = None
            try:
                w = child.get_backend_widget()
            except Exception:
                w = None
            if w is None:
                try:
                    if hasattr(child, "_create_backend_widget"):
                        child._create_backend_widget()
                        w = child.get_backend_widget()
                except Exception:
                    w = None
            if w is not None:
                try:
                    self._content_box.append(w)
                except Exception:
                    try:
                        self._content_box.add(w)
                    except Exception:
                        pass
            # propagate expansion hints
            try:
                if child.stretchable(YUIDimension.YD_VERT):
                    if hasattr(w, "set_vexpand"):
                        w.set_vexpand(True)
                if child.stretchable(YUIDimension.YD_HORIZ):
                    if hasattr(w, "set_hexpand"):
                        w.set_hexpand(True)
            except Exception:
                pass
        except Exception:
            pass

        # apply enablement state
        if self.isEnabled():
            self._apply_children_enablement(self.value())

    def _on_toggled(self, widget):
        try:
            val = bool(self._checkbox.get_active())
            self._checked = val
            if self._auto_enable:
                self._apply_children_enablement(val)
            try:
                if self.notify():
                    dlg = self.findDialog()
                    if dlg:
                        dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
            except Exception:
                pass
        except Exception:
            pass

    def _apply_children_enablement(self, isChecked: bool):
        try:
            if not self._auto_enable:
                return
            state = bool(isChecked)
            if self._invert_auto:
                state = not state
            child = self.child()
            if child is not None:
                child.setEnabled(state)
            #try:
            #    w = child.get_backend_widget()
            #    if w is not None:
            #        try:
            #            w.set_sensitive(state)
            #        except Exception:
            #            pass
            #except Exception:
            #    pass
        except Exception:
            pass

    def addChild(self, child):
        super().addChild(child)
        self._attach_child_backend()

    def _set_backend_enabled(self, enabled: bool):
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.set_sensitive(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass
        # propagate to logical children
        try:
            child = self.child()
            if child is not None:
                child.setEnabled(enabled)
        except Exception:
            pass

    def setProperty(self, propertyName, val):
        try:
            if propertyName == "label":
                self.setLabel(str(val))
                return True
            if propertyName in ("value", "checked"):
                self.setValue(bool(val))
                return True
        except Exception:
            pass
        return False

    def getProperty(self, propertyName):
        try:
            if propertyName == "label":
                return self.label()
            if propertyName in ("value", "checked"):
                return self.value()
        except Exception:
            pass
        return None

    def propertySet(self):
        try:
            props = YPropertySet()
            try:
                props.add(YProperty("label", YPropertyType.YStringProperty))
                props.add(YProperty("value", YPropertyType.YBoolProperty))
            except Exception:
                pass
            return props
        except Exception:
            return None

