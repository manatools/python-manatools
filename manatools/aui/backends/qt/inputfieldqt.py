# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains all Qt backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''
from PySide6 import QtWidgets
from ...yui_common import *

class YInputFieldQt(YWidget):
    def __init__(self, parent=None, label="", password_mode=False):
        super().__init__(parent)
        self._label = label
        self._value = ""
        self._password_mode = password_mode
    
    def widgetClass(self):
        return "YInputField"
    
    def value(self):
        return self._value
    
    def setValue(self, text):
        self._value = text
        if hasattr(self, '_entry_widget') and self._entry_widget:
            self._entry_widget.setText(text)
    
    def label(self):
        return self._label
    
    def _create_backend_widget(self):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if self._label:
            label = QtWidgets.QLabel(self._label)
            layout.addWidget(label)
        
        if self._password_mode:
            entry = QtWidgets.QLineEdit()
            entry.setEchoMode(QtWidgets.QLineEdit.Password)
        else:
            entry = QtWidgets.QLineEdit()
        
        entry.setText(self._value)
        entry.textChanged.connect(self._on_text_changed)
        layout.addWidget(entry)
        
        self._backend_widget = container
        self._entry_widget = entry
        self._backend_widget.setEnabled(bool(self._enabled))

    def _set_backend_enabled(self, enabled):
        """Enable/disable the input field: entry and container."""
        try:
            if getattr(self, "_entry_widget", None) is not None:
                try:
                    self._entry_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass

    def _on_text_changed(self, text):
        self._value = text
