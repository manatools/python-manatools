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


class YPushButtonQt(YWidget):
    def __init__(self, parent=None, label=""):
        super().__init__(parent)
        self._label = label
    
    def widgetClass(self):
        return "YPushButton"
    
    def label(self):
        return self._label
    
    def setLabel(self, label):
        self._label = label
        if self._backend_widget:
            self._backend_widget.setText(label)
    
    def _create_backend_widget(self):
        self._backend_widget = QtWidgets.QPushButton(self._label)
        # Set size policy to prevent unwanted expansion
        try:
            try:
                sp = self._backend_widget.sizePolicy()
                # PySide6 may expect enum class; try both styles defensively
                try:
                    sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Minimum if self.stretchable(YUIDimension.YD_HORIZ) else QtWidgets.QSizePolicy.Policy.Fixed)
                    sp.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Minimum if self.stretchable(YUIDimension.YD_VERT) else QtWidgets.QSizePolicy.Policy.Fixed)
                except Exception:
                    try:
                        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Minimum)
                    except Exception:
                        pass
                self._backend_widget.setSizePolicy(sp)
            except Exception:
                try:
                    # fallback: set using convenience form (two args)
                    self._backend_widget.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
                except Exception:
                    pass
        except Exception:
             pass
        self._backend_widget.setEnabled(bool(self._enabled))
        self._backend_widget.clicked.connect(self._on_clicked)

    def _set_backend_enabled(self, enabled):
        """Enable/disable the QPushButton backend."""
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass

    def _on_clicked(self):
        # Post a YWidgetEvent to the containing dialog (walk parents)
        dlg = self.findDialog()
        if dlg is not None:
            dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
        else:
            # fallback logging for now
            print(f"Button clicked (no dialog found): {self._label}")
