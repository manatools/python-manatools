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

class YVBoxGtk(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def widgetClass(self):
        return "YVBox"
    
    # Returns the stretchability of the layout box:
    def stretchable(self, dim):
        for child in self._children:
            expand = bool(child.stretchable(dim))
            weight = bool(child.weight(dim))
            if expand or weight:
                return True
        return False

    def _create_backend_widget(self):
        self._backend_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        for child in self._children:
            widget = child.get_backend_widget()
            expand = bool(child.stretchable(YUIDimension.YD_VERT))
            fill = True
            padding = 0

            try:
                if expand:
                    if hasattr(widget, "set_vexpand"):
                        widget.set_vexpand(True)
                    if hasattr(widget, "set_valign"):
                        widget.set_valign(Gtk.Align.FILL)
                    if hasattr(widget, "set_hexpand"):
                        widget.set_hexpand(True)
                    if hasattr(widget, "set_halign"):
                        widget.set_halign(Gtk.Align.FILL)
                else:
                    if hasattr(widget, "set_vexpand"):
                        widget.set_vexpand(False)
                    if hasattr(widget, "set_valign"):
                        widget.set_valign(Gtk.Align.START)
                    if hasattr(widget, "set_hexpand"):
                        widget.set_hexpand(False)
                    if hasattr(widget, "set_halign"):
                        widget.set_halign(Gtk.Align.START)
            except Exception:
                pass

            # Gtk4: use append instead of pack_start
            try:
                self._backend_widget.append(widget)
            except Exception:
                try:
                    self._backend_widget.add(widget)
                except Exception:
                    pass

    def _set_backend_enabled(self, enabled):
        """Enable/disable the VBox and propagate to children."""
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass
        # propagate logical enabled state to child widgets so they update their backends
        try:
            for c in list(getattr(self, "_children", []) or []):
                try:
                    c.setEnabled(enabled)
                except Exception:
                    pass
        except Exception:
            pass
