# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains all Qt backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''
from PySide6 import QtWidgets, QtCore
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
            layout = QtWidgets.QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)
            if self._label:
                lbl = QtWidgets.QLabel(self._label)
                try:
                    lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
                except Exception:
                    try:
                        lbl.setAlignment(QtCore.Qt.AlignLeft)
                    except Exception:
                        pass
                # keep label from expanding vertically
                try:
                    sp_lbl = lbl.sizePolicy()
                    try:
                        sp_lbl.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Preferred)
                        sp_lbl.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Fixed)
                    except Exception:
                        try:
                            sp_lbl.setHorizontalPolicy(QtWidgets.QSizePolicy.Preferred)
                            sp_lbl.setVerticalPolicy(QtWidgets.QSizePolicy.Fixed)
                        except Exception:
                            pass
                    lbl.setSizePolicy(sp_lbl)
                except Exception:
                    pass
                layout.addWidget(lbl)
                self._label_widget = lbl

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
            # apply initial size policy from stretchable hints
            try:
                self._apply_size_policy()
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
        try:
            if getattr(self, '_label_widget', None) is not None:
                try:
                    self._label_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass

    def _on_value_changed(self, val):
        try:
            self._value = int(val)
        except Exception:
            return
        # If notify is enabled, post a ValueChanged widget event
        try:
            if self.notify():
                dlg = self.findDialog()
                if dlg is not None:
                    try:
                        dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
                    except Exception:
                        try:
                            self._logger.debug("Failed to post ValueChanged event")
                        except Exception:
                            pass
        except Exception:
            pass

    def _apply_size_policy(self):
        """Apply size policy to container and spinbox according to stretchable flags."""
        try:
            # horizontal policy
            try:
                horiz = QtWidgets.QSizePolicy.Policy.Expanding if self.stretchable(YUIDimension.YD_HORIZ) else QtWidgets.QSizePolicy.Policy.Fixed
            except Exception:
                self._logger.debug("Failed to get horizontal stretchable policy")
                try:
                    horiz = QtWidgets.QSizePolicy.Expanding if self.stretchable(YUIDimension.YD_HORIZ) else QtWidgets.QSizePolicy.Fixed
                except Exception:
                    self._logger.debug("Failed to get horizontal stretchable policy fallback")
                    horiz = QtWidgets.QSizePolicy.Preferred
            # vertical policy
            try:
                vert = QtWidgets.QSizePolicy.Policy.Expanding if self.stretchable(YUIDimension.YD_VERT) else QtWidgets.QSizePolicy.Policy.Fixed
            except Exception:
                try:
                    vert = QtWidgets.QSizePolicy.Expanding if self.stretchable(YUIDimension.YD_VERT) else QtWidgets.QSizePolicy.Fixed
                except Exception:
                    vert = QtWidgets.QSizePolicy.Preferred

            if getattr(self, '_backend_widget', None) is not None:
                try:
                    sp = self._backend_widget.sizePolicy()
                    try:
                        sp.setHorizontalPolicy(horiz)
                        sp.setVerticalPolicy(vert)
                    except Exception:
                        pass
                    try:
                        self._backend_widget.setSizePolicy(sp)
                    except Exception:
                        pass
                except Exception:
                    pass

            if getattr(self, '_spinbox', None) is not None:
                try:
                    sp2 = self._spinbox.sizePolicy()
                    try:
                        sp2.setHorizontalPolicy(horiz)
                        sp2.setVerticalPolicy(vert)
                    except Exception:
                        pass
                    try:
                        self._spinbox.setSizePolicy(sp2)
                    except Exception:
                        pass
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
