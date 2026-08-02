# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.gtk contains all GTK backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
'''

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, GObject, GdkPixbuf, GLib
import cairo
import threading
import os
import logging
from ...yui_common import *
from .commongtk import _convert_mnemonic_to_gtk


class YCheckBoxGtk(YWidget):
    def __init__(self, parent=None, label="", is_checked=False):
        super().__init__(parent)
        self._label = _convert_mnemonic_to_gtk(label)
        self._is_checked = is_checked
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
    
    def widgetClass(self):
        return "YCheckBox"
    
    def value(self):
        return self._is_checked
    
    def setValue(self, checked):
        self._is_checked = checked
        if self._backend_widget:
            try:
                self._backend_widget.set_active(checked)
            except Exception:
                pass

    def isChecked(self):
        '''
            Simplified access to value(): Return 'true' if the CheckBox is checked.        
        '''
        return self.value()

    def setChecked(self, checked: bool = True):
        '''
            Simplified access to setValue(): Set the CheckBox to 'checked' state if 'checked' is true.
        '''
        self.setValue(checked)

    def label(self):
        return self._label
    
    def _create_backend_widget(self):
        self._backend_widget = Gtk.CheckButton(label=self._label)
        self._backend_widget.set_use_underline(True)
        try:
            self._backend_widget.set_active(self._is_checked)
            self._backend_widget.connect("toggled", self._on_toggled)
        except Exception:
            self._logger.error("_create_backend_widget toggle setup failed", exc_info=True)
        self._backend_widget.set_sensitive(self._enabled)
        if self._help_text:
            self._backend_widget.set_tooltip_text(self._help_text)
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def setHelpText(self, help_text: str):
        super().setHelpText(help_text)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.set_tooltip_text(help_text)
        except Exception:
            self._logger.exception("setHelpText failed", exc_info=True)
    
    def _on_toggled(self, button):
        try:
            self._is_checked = button.get_active()
        except Exception:
            self._is_checked = bool(self._is_checked)
        
        if self.notify():
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))

    def _set_backend_enabled(self, enabled):
        """Enable/disable the check button backend."""
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass
