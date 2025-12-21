# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains all Qt backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''
from PySide6 import QtWidgets
import logging
from ...yui_common import *

class YLabelQt(YWidget):
    def __init__(self, parent=None, text="", isHeading=False, isOutputField=False):
        super().__init__(parent)
        self._text = text
        self._is_heading = isHeading
        self._is_output_field = isOutputField
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
    
    def widgetClass(self):
        return "YLabel"
    
    def text(self):
        return self._text
    
    def setText(self, new_text):
        self._text = new_text
        if self._backend_widget:
            self._backend_widget.setText(new_text)
    
    def _create_backend_widget(self):
        self._backend_widget = QtWidgets.QLabel(self._text)
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
