import logging
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
from ...yui_common import *


class YIntFieldGtk(YWidget):
    def __init__(self, parent=None, label="", minValue=0, maxValue=100, initialValue=0):
        super().__init__(parent)
        self._label = label
        self._min = int(minValue)
        self._max = int(maxValue)
        self._value = int(initialValue)
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")

    def widgetClass(self):
        return "YIntField"

    def value(self):
        return int(self._value)

    def setValue(self, val):
        try:
            v = int(val)
        except Exception:
            try:
                self._logger.debug("setValue: invalid int %r", val)
            except Exception:
                pass
            return
        if v < self._min:
            v = self._min
        if v > self._max:
            v = self._max
        self._value = v
        try:
            if getattr(self, '_spin', None) is not None:
                try:
                    self._spin.set_value(self._value)
                except Exception:
                    pass
        except Exception:
            pass

    def minValue(self):
        return int(self._min)

    def maxValue(self):
        return int(self._max)

    def setMinValue(self, val):
        try:
            self._min = int(val)
        except Exception:
            return
        try:
            if getattr(self, '_adj', None) is not None:
                try:
                    self._adj.set_lower(self._min)
                except Exception:
                    pass
        except Exception:
            pass

    def setMaxValue(self, val):
        try:
            self._max = int(val)
        except Exception:
            return
        try:
            if getattr(self, '_adj', None) is not None:
                try:
                    self._adj.set_upper(self._max)
                except Exception:
                    pass
        except Exception:
            pass

    def label(self):
        return self._label

    def _create_backend_widget(self):
        try:
            # vertical layout: label above spin so they're attached
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            if self._label:
                lbl = Gtk.Label(label=self._label)
                try:
                    lbl.set_halign(Gtk.Align.START)
                except Exception:
                    try:
                        lbl.set_xalign(0.0)
                    except Exception:
                        pass
                # keep label from expanding vertically
                try:
                    lbl.set_hexpand(False)
                    lbl.set_vexpand(False)
                except Exception:
                    pass
                box.append(lbl)

            # Create adjustment and spinbutton
            adj = Gtk.Adjustment(value=self._value, lower=self._min, upper=self._max, step_increment=1, page_increment=10)
            spin = Gtk.SpinButton(adjustment=adj)
            try:
                spin.set_value(self._value)
            except Exception:
                pass
            try:
                spin.connect('value-changed', self._on_value_changed)
            except Exception:
                pass
            # Attach spin below the label and let _apply_size_policy control expansion
            box.append(spin)

            self._backend_widget = box
            self._spin = spin
            self._adj = adj
            try:
                self._label_widget = lbl
            except Exception:
                self._label_widget = None
            # apply size policy according to stretchable hints (do not expand by default)
            try:
                self._apply_size_policy()
            except Exception:
                pass
            try:
                self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
            except Exception:
                pass
        except Exception as e:
            try:
                logging.getLogger('manatools.aui.gtk.intfield').exception("Error creating GTK IntField backend: %s", e)
            except Exception:
                pass

    def _set_backend_enabled(self, enabled):
        try:
            if getattr(self, '_spin', None) is not None:
                try:
                    self._spin.set_sensitive(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if getattr(self, '_label_widget', None) is not None:
                try:
                    self._label_widget.set_sensitive(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass

    def _on_value_changed(self, spin):
        try:
            v = int(spin.get_value())
            self._value = v
            if self.notify():
                dlg = self.findDialog()
                if dlg is not None:
                    dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
        except Exception:
            pass

    def _apply_size_policy(self):
        """Apply hexpand/vexpand flags according to `stretchable` hints.

        Default: do not expand (respect user's setStretchable)."""
        try:
            horiz = bool(self.stretchable(YUIDimension.YD_HORIZ))
        except Exception:
            horiz = False
        try:
            vert = bool(self.stretchable(YUIDimension.YD_VERT))
        except Exception:
            vert = False

        try:
            if getattr(self, '_backend_widget', None) is not None:
                try:
                    self._backend_widget.set_hexpand(horiz)
                except Exception:
                    pass
                try:
                    self._backend_widget.set_vexpand(vert)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            if getattr(self, '_spin', None) is not None:
                try:
                    self._spin.set_hexpand(horiz)
                except Exception:
                    pass
                try:
                    self._spin.set_vexpand(vert)
                except Exception:
                    pass
        except Exception:
            pass

    def setStretchable(self, dim, new_stretch):
        try:
            super().setStretchable(dim, new_stretch)
        except Exception:
            pass
        try:
            self._apply_size_policy()
        except Exception:
            pass
