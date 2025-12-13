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


class YPushButtonGtk(YWidget):
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
            try:
                self._backend_widget.set_label(label)
            except Exception:
                pass
    
    def _create_backend_widget(self):
        self._backend_widget = Gtk.Button(label=self._label)
        # Prevent button from being stretched horizontally by default.
        try:
            self._backend_widget.set_hexpand(self.stretchable(YUIDimension.YD_HORIZ))            
            self._backend_widget.set_vexpand(self.stretchable(YUIDimension.YD_VERT))
            self._backend_widget.set_halign(Gtk.Align.FILL if self.stretchable(YUIDimension.YD_HORIZ) else Gtk.Align.CENTER)
            self._backend_widget.set_valign(Gtk.Align.FILL if self.stretchable(YUIDimension.YD_VERT) else Gtk.Align.CENTER)
        except Exception:
            pass
        try:
            self._backend_widget.set_sensitive(self._enabled)
            self._backend_widget.connect("clicked", self._on_clicked)
        except Exception:
            pass
    
    def _on_clicked(self, button):
        if self.notify() is False:
            return
        dlg = self.findDialog()
        if dlg is not None:
            dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
        else:
            # silent fallback
            pass

    def _set_backend_enabled(self, enabled):
        """Enable/disable the push button backend."""
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass
