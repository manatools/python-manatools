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

class YRadioButtonQt(YWidget):
    def __init__(self, parent=None, label="", isChecked=False):
        super().__init__(parent)
        self._label = label
        self._is_checked = bool(isChecked)
        self._backend_widget = None

    def widgetClass(self):
        return "YRadioButton"

    def label(self):
        return self._label

    def setLabel(self, newLabel):
        try:
            self._label = str(newLabel)
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setText(self._label)
                except Exception:
                    pass
        except Exception:
            pass

    def isChecked(self):
        return bool(self._is_checked)

    def setChecked(self, checked):
        try:
            self._is_checked = bool(checked)
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    # avoid emitting signals while programmatically changing state
                    self._backend_widget.blockSignals(True)
                    self._backend_widget.setChecked(self._is_checked)
                finally:
                    try:
                        self._backend_widget.blockSignals(False)
                    except Exception:
                        pass
        except Exception:
            pass

    # Compatibility with other widgets: provide value()/setValue()
    def value(self):
        return self.isChecked()

    def setValue(self, checked):
        return self.setChecked(checked)

    def _create_backend_widget(self):
        try:
            self._backend_widget = QtWidgets.QRadioButton(self._label)
            self._backend_widget.setChecked(self._is_checked)
            self._backend_widget.toggled.connect(self._on_toggled)
            try:
                self._backend_widget.setEnabled(bool(self._enabled))
            except Exception:
                pass
        except Exception:
            self._backend_widget = None

    def _set_backend_enabled(self, enabled):
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass

    def _on_toggled(self, checked):
        try:
            self._is_checked = bool(checked)
        except Exception:
            self._is_checked = False

        if self.notify():
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
            else:
                # best-effort debug output when no dialog
                try:
                    print(f"RadioButton toggled: {self._label} = {self._is_checked}")
                except Exception:
                    pass