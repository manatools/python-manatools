# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
"""
Qt backend Slider widget.
- Horizontal slider synchronized with a spin box.
- Emits ValueChanged on changes and Activated on user release.
- Default stretchable horizontally.
"""
from PySide6 import QtWidgets, QtCore
import logging
from ...yui_common import *

class YSliderQt(YWidget):
    def __init__(self, parent=None, label: str = "", minVal: int = 0, maxVal: int = 100, initialVal: int = 0):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        self._label_text = str(label) if label else ""
        self._min = int(minVal)
        self._max = int(maxVal)
        if self._min > self._max:
            self._min, self._max = self._max, self._min
        self._value = max(self._min, min(self._max, int(initialVal)))
        # stretchable horizontally by default
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, False)

    def widgetClass(self):
        return "YSlider"

    def value(self) -> int:
        return int(self._value)

    def setValue(self, v: int):
        prev = self._value
        self._value = max(self._min, min(self._max, int(v)))
        try:
            if getattr(self, "_slider", None) is not None:
                self._slider.setValue(self._value)
            if getattr(self, "_spin", None) is not None:
                self._spin.setValue(self._value)
        except Exception:
            pass
        if self._value != prev and self.notify():
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))

    def _create_backend_widget(self):
        try:
            root = QtWidgets.QWidget()
            lay = QtWidgets.QHBoxLayout(root)
            lay.setContentsMargins(10, 10, 10, 10)
            lay.setSpacing(8)

            if self._label_text:
                lbl = QtWidgets.QLabel(self._label_text)
                lay.addWidget(lbl)

            slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            slider.setRange(self._min, self._max)
            slider.setValue(self._value)
            slider.setTracking(True)

            spin = QtWidgets.QSpinBox()
            spin.setRange(self._min, self._max)
            spin.setValue(self._value)

            # expand policy for slider so it takes available space
            try:
                sp = slider.sizePolicy()
                sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Expanding)
                slider.setSizePolicy(sp)
            except Exception:
                pass

            lay.addWidget(slider, stretch=1)
            lay.addWidget(spin)

            # wire signals
            def _on_slider_changed(val):
                try:
                    spin.setValue(val)
                except Exception:
                    pass
                old = self._value
                self._value = int(val)
                if self.notify() and old != self._value:
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
            def _on_slider_released():
                if self.notify():
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
            def _on_spin_changed(val):
                try:
                    slider.setValue(int(val))
                except Exception:
                    pass
                old = self._value
                self._value = int(val)
                if self.notify() and old != self._value:
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))

            slider.valueChanged.connect(_on_slider_changed)
            slider.sliderReleased.connect(_on_slider_released)
            spin.valueChanged.connect(_on_spin_changed)

            self._slider = slider
            self._spin = spin
            self._backend_widget = root
            self._backend_widget.setEnabled(bool(self._enabled))
            try:
                self._logger.debug("_create_backend_widget: <%s> range=[%d,%d] value=%d", self.debugLabel(), self._min, self._max, self._value)
            except Exception:
                pass
        except Exception:
            try:
                self._logger.exception("YSliderQt _create_backend_widget failed")
            except Exception:
                pass

    def _set_backend_enabled(self, enabled):
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.setEnabled(bool(enabled))
        except Exception:
            pass
