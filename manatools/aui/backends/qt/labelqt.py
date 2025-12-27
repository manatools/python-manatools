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

class YLabelQt(YWidget):
    def __init__(self, parent=None, text="", isHeading=False, isOutputField=False):
        super().__init__(parent)
        self._text = text
        self._is_heading = isHeading
        self._is_output_field = isOutputField
        self._auto_wrap = False
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
    
    def widgetClass(self):
        return "YLabel"
    
    def text(self):
        return self._text
    
    def isHeading(self) -> bool:
        return bool(self._is_heading)
    
    def isOutputField(self) -> bool:
        return bool(self._is_output_field)
    
    def label(self):
        return self.text()
    
    def value(self):
        return self.text()
    
    def setText(self, new_text):
        self._text = new_text
        if self._backend_widget:
            self._backend_widget.setText(new_text)
    
    def setValue(self, newValue):
        self.setText(newValue)

    def setLabel(self, newLabel):
        self.setText(newLabel)
    
    def autoWrap(self) -> bool:
        return bool(self._auto_wrap)

    def setAutoWrap(self, on: bool = True):
        self._auto_wrap = bool(on)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.setWordWrap(self._auto_wrap)
        except Exception:
            pass
    
    def _create_backend_widget(self):
        self._backend_widget = QtWidgets.QLabel(self._text)
        try:
            self._backend_widget.setWordWrap(bool(self._auto_wrap))
        except Exception:
            pass
        # Output field: allow text selection like a read-only input
        try:
            if self._is_output_field:
                flags = (
                    QtCore.Qt.TextSelectableByMouse |
                    QtCore.Qt.TextSelectableByKeyboard
                )
                self._backend_widget.setTextInteractionFlags(flags)
                # Focus policy to allow keyboard selection
                self._backend_widget.setFocusPolicy(QtCore.Qt.StrongFocus)
            else:
                self._backend_widget.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        except Exception:
            pass
        if self._is_heading:
            font = self._backend_widget.font()
            font.setBold(True)
            font.setPointSize(font.pointSize() + 2)
            self._backend_widget.setFont(font)
        self._backend_widget.setEnabled(bool(self._enabled))
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        """Enable/disable the QLabel backend."""
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass
