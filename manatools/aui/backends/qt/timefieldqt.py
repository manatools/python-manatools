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
import datetime
from ...yui_common import *


class YTimeFieldQt(YWidget):
    """Qt backend YTimeField implementation using QTimeEdit.
    value()/setValue() use HH:MM:SS. No change events posted.
    """
    def __init__(self, parent=None, label: str = ""):
        super().__init__(parent)
        self._label = label or ""
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        self._time = datetime.time(0, 0, 0)
        try:
            self.setStretchable(YUIDimension.YD_HORIZ, True)
            self.setStretchable(YUIDimension.YD_VERT, False)
        except Exception:
            pass

    def widgetClass(self):
        return "YTimeField"

    def value(self) -> str:
        try:
            t = getattr(self, '_time', None)
            if t is None:
                return ''
            return f"{t.hour:02d}:{t.minute:02d}:{t.second:02d}"
        except Exception:
            return ""

    def setValue(self, timestr: str):
        try:
            parts = str(timestr).split(':')
            if len(parts) != 3:
                return
            h, m, s = [int(p) for p in parts]
            h = max(0, min(23, h))
            m = max(0, min(59, m))
            s = max(0, min(59, s))
            self._time = datetime.time(h, m, s)
            if getattr(self, '_edit', None) is not None:
                try:
                    self._edit.setTime(QtCore.QTime(h, m, s))
                except Exception:
                    pass
        except Exception as e:
            self._logger.exception("setValue failed: %s", e)

    def _create_backend_widget(self):
        cont = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(cont)
        lay.setContentsMargins(0, 0, 0, 0)
        if self._label:
            lbl = QtWidgets.QLabel(self._label)
            lay.addWidget(lbl)
            self._label_widget = lbl
        edit = QtWidgets.QTimeEdit()
        try:
            edit.setDisplayFormat("HH:mm:ss")
            edit.setTime(QtCore.QTime(self._time.hour, self._time.minute, self._time.second))
        except Exception:
            pass
        def _on_time_changed(qt: QtCore.QTime):
            try:
                self._time = datetime.time(qt.hour(), qt.minute(), qt.second())
            except Exception:
                pass
        try:
            edit.timeChanged.connect(_on_time_changed)
        except Exception:
            pass
        # Respect stretchable flags via size policy
        try:
            sp = edit.sizePolicy()
            try:
                horiz = QtWidgets.QSizePolicy.Policy.Expanding if self.stretchable(YUIDimension.YD_HORIZ) else QtWidgets.QSizePolicy.Policy.Preferred
                vert = QtWidgets.QSizePolicy.Policy.Fixed if not self.stretchable(YUIDimension.YD_VERT) else QtWidgets.QSizePolicy.Policy.Expanding
                sp.setHorizontalPolicy(horiz)
                sp.setVerticalPolicy(vert)
            except Exception:
                try:
                    horiz = QtWidgets.QSizePolicy.Expanding if self.stretchable(YUIDimension.YD_HORIZ) else QtWidgets.QSizePolicy.Preferred
                    vert = QtWidgets.QSizePolicy.Fixed if not self.stretchable(YUIDimension.YD_VERT) else QtWidgets.QSizePolicy.Expanding
                    sp.setHorizontalPolicy(horiz)
                    sp.setVerticalPolicy(vert)
                except Exception:
                    pass
            edit.setSizePolicy(sp)
        except Exception:
            pass
        lay.addWidget(edit)
        self._edit = edit
        self._backend_widget = cont
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        try:
            if getattr(self, '_edit', None) is not None:
                self._edit.setEnabled(bool(enabled))
            if getattr(self, '_label_widget', None) is not None:
                self._label_widget.setEnabled(bool(enabled))
        except Exception:
            pass
