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
from ...yui_common import *

class YRadioButtonGtk(YWidget):
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
                    self._backend_widget.set_label(self._label)
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
                    self._backend_widget.handler_block_by_func(self._on_toggled)
                    self._backend_widget.set_active(self._is_checked)
                finally:
                    try:
                        self._backend_widget.handler_unblock_by_func(self._on_toggled)
                    except Exception:
                        pass
        except Exception:
            pass

    def _create_backend_widget(self):
        self._backend_widget = Gtk.CheckButton(label=self._label)
 
        # Prevent radio button from being stretched horizontally by default.
        try:
            self._backend_widget.set_hexpand(self.stretchable(YUIDimension.YD_HORIZ))            
            self._backend_widget.set_vexpand(self.stretchable(YUIDimension.YD_VERT))
            self._backend_widget.set_halign(Gtk.Align.FILL if self.stretchable(YUIDimension.YD_HORIZ) else Gtk.Align.CENTER)
            self._backend_widget.set_valign(Gtk.Align.FILL if self.stretchable(YUIDimension.YD_VERT) else Gtk.Align.CENTER)
        except Exception:
            pass
        try:
            self._backend_widget.set_sensitive(self._enabled)
            self._backend_widget.connect("toggled", self._on_toggled)
            self._backend_widget.set_active(self._is_checked)
        except Exception:
            pass

    def _on_toggled(self, button):
        try:
            self._is_checked = bool(button.get_active())
        except Exception:
            try:
                self._is_checked = bool(self._is_checked)
            except Exception:
                self._is_checked = False

        if self.notify() is False:
            return

        try:
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        """Enable/disable the Gtk.RadioButton backend."""
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass