# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains all Qt backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''
from PySide6 import QtWidgets, QtGui
import logging
from typing import Optional
from ...yui_common import *
from .commonqt import _resolve_icon


class YPushButtonQt(YWidget):
    def __init__(self, parent=None, label: str="", icon_name: Optional[str]=None, icon_only: Optional[bool]=False):
        super().__init__(parent)
        self._label = label
        self._icon_name = icon_name
        self._icon_only = bool(icon_only)
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
    
    def widgetClass(self):
        return "YPushButton"
    
    def label(self):
        return self._label
    
    def setLabel(self, label):
        self._label = label
        if self._backend_widget and self._icon_only is False:
            self._backend_widget.setText(label)
    
    def _create_backend_widget(self):
        if self._icon_only:
            self._backend_widget = QtWidgets.QPushButton()
        else:
            self._backend_widget = QtWidgets.QPushButton(self._label)
        if self._help_text:
            self._backend_widget.setToolTip(self._help_text)
        if self.visible():
            self._backend_widget.show()
        else:
            self._backend_widget.hide()
        # apply icon if previously set
        try:
            if getattr(self, "_icon_name", None):
                ico = _resolve_icon(self._icon_name)
                if ico is not None and not ico.isNull():
                    try:
                        self._backend_widget.setIcon(ico)
                    except Exception:
                        pass
        except Exception:
            pass
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
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

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
            self._logger.warning("Button clicked (no dialog found): %s", self._label)

    def setIcon(self, icon_name: str):
        """Set/clear the icon for this pushbutton (icon_name may be theme name or path)."""
        try:
            self._icon_name = icon_name
            if getattr(self, "_backend_widget", None) is None:
                return
            ico = _resolve_icon(icon_name)
            if ico is not None and not ico.isNull():
                try:
                    self._backend_widget.setIcon(ico)
                    return
                except Exception:
                    pass
            # Clear icon if resolution failed
            try:
                self._backend_widget.setIcon(QtGui.QIcon())
            except Exception:
                pass
        except Exception:
            try:
                self._logger.exception("setIcon failed")
            except Exception:
                pass

    def setVisible(self, visible=True):
        super().setVisible(visible)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.setVisible(visible)
        except Exception:
            self._logger.exception("setVisible failed")
    
    def setHelpText(self, help_text: str):
        super().setHelpText(help_text)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.setToolTip(help_text)
        except Exception:
            self._logger.exception("setHelpText failed")
