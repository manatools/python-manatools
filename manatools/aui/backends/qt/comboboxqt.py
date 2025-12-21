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

class YComboBoxQt(YSelectionWidget):
    def __init__(self, parent=None, label="", editable=False):
        super().__init__(parent)
        self._label = label
        self._editable = editable
        self._value = ""
        self._selected_items = []
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
    
    def widgetClass(self):
        return "YComboBox"
    
    def value(self):
        return self._value
    
    def setValue(self, text):
        self._value = text
        if hasattr(self, '_combo_widget') and self._combo_widget:
            index = self._combo_widget.findText(text)
            if index >= 0:
                self._combo_widget.setCurrentIndex(index)
            elif self._editable:
                self._combo_widget.setEditText(text)
        # update selected_items to keep internal state consistent
        self._selected_items = []
        for item in self._items:
            if item.label() == text:
                self._selected_items.append(item)
                break
    
    def editable(self):
        return self._editable
    
    def _create_backend_widget(self):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if self._label:
            label = QtWidgets.QLabel(self._label)
            layout.addWidget(label)
        
        if self._editable:
            combo = QtWidgets.QComboBox()
            combo.setEditable(True)
        else:
            combo = QtWidgets.QComboBox()
        
        # Add items to combo box
        for item in self._items:
            combo.addItem(item.label())
        
        combo.currentTextChanged.connect(self._on_text_changed)
        # also handle index change (safer for some input methods)
        combo.currentIndexChanged.connect(lambda idx: self._on_text_changed(combo.currentText()))
        layout.addWidget(combo)
        
        self._backend_widget = container
        self._combo_widget = combo
        self._backend_widget.setEnabled(bool(self._enabled))
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        """Enable/disable the combobox and its container."""
        try:
            if getattr(self, "_combo_widget", None) is not None:
                try:
                    self._combo_widget.setEnabled(bool(enabled))
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
        # Update selected items
        self._selected_items = []
        for item in self._items:
            if item.label() == text:
                self._selected_items.append(item)
                break
        if self.notify():
            # Post selection-changed event to containing dialog
            try:
                dlg = self.findDialog()
                if dlg is not None:
                    dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
            except Exception:
                pass
