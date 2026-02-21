# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.gtk contains all GTK backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
'''
"""
GTK4 backend Slider widget.
- Horizontal Gtk.Scale synchronized with Gtk.SpinButton via Gtk.Adjustment.
- Emits ValueChanged on changes and Activated on user release (value-changed).
- Default stretchable horizontally.
"""
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
import logging
from ...yui_common import *

class YSliderGtk(YWidget):
    def __init__(self, parent=None, label: str = "", minVal: int = 0, maxVal: int = 100, initialVal: int = 0):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        self._label_text = str(label) if label else ""
        self._min = int(minVal)
        self._max = int(maxVal)
        if self._min > self._max:
            self._min, self._max = self._max, self._min
        self._value = max(self._min, min(self._max, int(initialVal)))
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, False)
        self._backend_widget = None
        self._adjustment = None

    def widgetClass(self):
        return "YSlider"

    def value(self) -> int:
        return int(self._value)

    def setValue(self, v: int):
        prev = self._value
        self._value = max(self._min, min(self._max, int(v)))
        try:
            if self._adjustment is not None:
                self._adjustment.set_value(self._value)
        except Exception:
            pass
        if self._value != prev and self.notify():
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))

    def _create_backend_widget(self):
        try:
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            try:
                box.set_hexpand(True)
                box.set_vexpand(False)
            except Exception:
                pass
            if self._label_text:
                lbl = Gtk.Label.new(self._label_text)
                try:
                    lbl.set_xalign(0.0)
                except Exception:
                    pass
                box.append(lbl)

            adj = Gtk.Adjustment.new(self._value, self._min, self._max, 1, 10, 0)
            scale = Gtk.Scale.new(Gtk.Orientation.HORIZONTAL, adj)
            try:
                scale.set_hexpand(True)
                scale.set_vexpand(False)
            except Exception:
                pass
            spin = Gtk.SpinButton.new(adj, 1, 0)
            try:
                spin.set_numeric(True)
            except Exception:
                pass

            box.append(scale)
            box.append(spin)

            def _on_value_changed(widget):
                try:
                    val = int(adj.get_value())
                except Exception:
                    val = self._value
                old = self._value
                self._value = val
                if self.notify() and old != self._value:
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
            try:
                scale.connect('value-changed', _on_value_changed)
                spin.connect('value-changed', _on_value_changed)
            except Exception:
                pass

            self._backend_widget = box
            self._adjustment = adj
            self._backend_widget.set_sensitive(self._enabled)
            try:
                self._logger.debug("_create_backend_widget: <%s> range=[%d,%d] value=%d", self.debugLabel(), self._min, self._max, self._value)
            except Exception:
                pass
        except Exception:
            try:
                self._logger.exception("YSliderGtk _create_backend_widget failed")
            except Exception:
                pass

    def _set_backend_enabled(self, enabled):
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.set_sensitive(bool(enabled))
        except Exception:
            pass
