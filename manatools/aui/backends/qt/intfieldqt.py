# vim: set fileencoding=utf-8 :
from PySide6 import QtWidgets
import logging
from ...yui_common import *


class YIntFieldQt(YWidget):
    def __init__(self, parent=None, label="", minValue=0, maxValue=100, initialValue=0):
        super().__init__(parent)
        self._label = label
        self._min = int(minValue)
        self._max = int(maxValue)
        self._value = int(initialValue)
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")

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
            if getattr(self, '_spinbox', None) is not None:
                try:
                    self._spinbox.setValue(self._value)
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
            if getattr(self, '_spinbox', None) is not None:
                try:
                    self._spinbox.setMinimum(self._min)
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
            if getattr(self, '_spinbox', None) is not None:
                try:
                    self._spinbox.setMaximum(self._max)
                except Exception:
                    pass
        except Exception:
            pass

    def label(self):
        return self._label

    def _create_backend_widget(self):
        try:
            container = QtWidgets.QWidget()
            layout = QtWidgets.QHBoxLayout(container)
            layout.setContentsMargins(0,0,0,0)
            if self._label:
                lbl = QtWidgets.QLabel(self._label)
                layout.addWidget(lbl)

            spin = QtWidgets.QSpinBox()
            try:
                spin.setRange(self._min, self._max)
                spin.setValue(self._value)
            except Exception:
                pass
            try:
                spin.valueChanged.connect(self._on_value_changed)
            except Exception:
                pass
            layout.addWidget(spin)

            self._backend_widget = container
            self._spinbox = spin
            try:
                self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
            except Exception:
                pass
        except Exception as e:
            try:
                logging.getLogger("manatools.aui.qt.intfield").exception("Error creating Qt IntField backend: %s", e)
            except Exception:
                pass

    def _set_backend_enabled(self, enabled):
        try:
            if getattr(self, '_spinbox', None) is not None:
                try:
                    self._spinbox.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass

    def _on_value_changed(self, val):
        try:
            self._value = int(val)
            if self.notify():
               dlg = self.findDialog()
               if dlg is not None:
                    dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
        except Exception    :
            pass
