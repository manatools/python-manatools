# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains Qt backend for YMultiLineEdit

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''
import logging
from ...yui_common import *
try:
    from PySide6 import QtWidgets, QtCore
except Exception:
    QtWidgets = None
    QtCore = None

_mod_logger = logging.getLogger("manatools.aui.qt.multiline.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)


class YMultiLineEditQt(YWidget):
    def __init__(self, parent=None, label=""):
        super().__init__(parent)
        self._label = label
        self._value = ""
        self._height = 4
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        if not self._logger.handlers and _mod_logger.handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)

        self._qwidget = None

    def widgetClass(self):
        return "YMultiLineEdit"

    def value(self):
        return str(self._value)

    def setValue(self, text):
        try:
            s = str(text) if text is not None else ""
        except Exception:
            s = ""
        self._value = s
        try:
            if self._qwidget is not None:
                try:
                    self._qtext.setPlainText(self._value)
                except Exception:
                    pass
        except Exception:
            pass

    def label(self):
        return self._label

    def setLabel(self, label):
        try:
            self._label = label
            if self._qwidget is not None:
                try:
                    self._qlbl.setText(str(label))
                except Exception:
                    pass
        except Exception:
            pass

    def _create_backend_widget(self):
        try:
            if QtWidgets is None:
                raise ImportError("PySide6 not available")
            self._qwidget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(self._qwidget)
            layout.setContentsMargins(0, 0, 0, 0)
            self._qlbl = QtWidgets.QLabel(str(self._label))
            self._qtext = QtWidgets.QPlainTextEdit()
            self._qtext.setPlainText(self._value)
            layout.addWidget(self._qlbl)
            layout.addWidget(self._qtext)
            try:
                self._qtext.textChanged.connect(self._on_text_changed)
            except Exception:
                pass
            self._backend_widget = self._qwidget
        except Exception as e:
            try:
                self._logger.exception("Error creating Qt MultiLineEdit backend: %s", e)
            except Exception:
                pass

    def _set_backend_enabled(self, enabled):
        try:
            if self._qwidget is not None:
                try:
                    self._qtext.setReadOnly(not enabled)
                except Exception:
                    pass
        except Exception:
            pass

    def _on_text_changed(self):
        try:
            text = self._qtext.toPlainText()
            self._value = text
            dlg = self.findDialog()
            if dlg is not None:
                try:
                    if self.notify():
                        dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
                except Exception:
                    try:
                        self._logger.exception("Failed to post ValueChanged event")
                    except Exception:
                        pass
        except Exception:
            try:
                self._logger.exception("_on_text_changed error")
            except Exception:
                pass
