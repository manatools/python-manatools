# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains all Qt backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''
from PySide6 import QtWidgets, QtCore
from ...yui_common import *

class YCheckBoxQt(YWidget):
    def __init__(self, parent=None, label="", is_checked=False):
        super().__init__(parent)
        self._label = label
        self._is_checked = is_checked
    
    def widgetClass(self):
        return "YCheckBox"
    
    def value(self):
        return self._is_checked
    
    def setValue(self, checked):
        self._is_checked = checked
        if self._backend_widget:
            try:
                # avoid emitting signals while programmatically changing state
                self._backend_widget.blockSignals(True)
                self._backend_widget.setChecked(checked)
            finally:
                try:
                    self._backend_widget.blockSignals(False)
                except Exception:
                    pass
    
    def label(self):
        return self._label
    
    def _create_backend_widget(self):
        self._backend_widget = QtWidgets.QCheckBox(self._label)
        self._backend_widget.setChecked(self._is_checked)
        self._backend_widget.stateChanged.connect(self._on_state_changed)
        self._backend_widget.setEnabled(bool(self._enabled))

    def _set_backend_enabled(self, enabled):
        """Enable/disable the QCheckBox backend."""
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass

    def _on_state_changed(self, state):
        # Update internal state
        # state is QtCore.Qt.CheckState (Unchecked=0, PartiallyChecked=1, Checked=2)
        self._is_checked = (QtCore.Qt.CheckState(state) == QtCore.Qt.CheckState.Checked)

        if self.notify():
            # Post a YWidgetEvent to the containing dialog
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
            else:
                print(f"CheckBox state changed (no dialog found): {self._label} = {self._is_checked}")
