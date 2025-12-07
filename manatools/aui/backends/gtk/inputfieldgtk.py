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


class YInputFieldGtk(YWidget):
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
            try:
                self._entry_widget.set_text(text)
            except Exception:
                pass
    
    def label(self):
        return self._label
    
    def _create_backend_widget(self):
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        if self._label:
            label = Gtk.Label(label=self._label)
            try:
                if hasattr(label, "set_xalign"):
                    label.set_xalign(0.0)
            except Exception:
                pass
            try:
                hbox.append(label)
            except Exception:
                hbox.add(label)
        
        if self._password_mode:
            entry = Gtk.Entry()
            try:
                entry.set_visibility(False)
            except Exception:
                pass
        else:
            entry = Gtk.Entry()
        
        try:
            entry.set_text(self._value)
            entry.connect("changed", self._on_changed)
        except Exception:
            pass
        
        try:
            hbox.append(entry)
        except Exception:
            hbox.add(entry)

        self._backend_widget = hbox
        self._entry_widget = entry
    
    def _on_changed(self, entry):
        try:
            self._value = entry.get_text()
        except Exception:
            self._value = ""

    def _set_backend_enabled(self, enabled):
        """Enable/disable the input field (entry and container)."""
        try:
            if getattr(self, "_entry_widget", None) is not None:
                try:
                    self._entry_widget.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass
