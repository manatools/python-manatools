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

class YVBoxGtk(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
    
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
            try:
                # Respect the child's stretchable/weight hints instead of forcing expansion
                vert_stretch = bool(child.stretchable(YUIDimension.YD_VERT)) or bool(child.weight(YUIDimension.YD_VERT))
                horiz_stretch = bool(child.stretchable(YUIDimension.YD_HORIZ)) or bool(child.weight(YUIDimension.YD_HORIZ))
                widget.set_vexpand(bool(vert_stretch))
                widget.set_hexpand(bool(horiz_stretch))
                try:
                    widget.set_valign(Gtk.Align.FILL if vert_stretch else Gtk.Align.START)
                except Exception:
                    pass
                try:
                    widget.set_halign(Gtk.Align.FILL if horiz_stretch else Gtk.Align.START)
                except Exception:
                    pass
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
        self._backend_widget.set_sensitive(self._enabled)
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
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
