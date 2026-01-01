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
from .commongtk import _resolve_icon, _resolve_gicon


class YPushButtonGtk(YWidget):
    def __init__(self, parent=None, label=""):
        super().__init__(parent)
        self._label = label
        self._icon_name = None
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
    
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
        # apply icon if previously set
        try:
            if getattr(self, "_icon_name", None):
                try:
                    img = _resolve_icon(self._icon_name)
                except Exception:
                    img = None
                if img is not None:
                    try:
                        # Prefer set_icon if available
                        try:
                            self._backend_widget.set_icon(img.get_paintable())
                        except Exception:
                            # Fallback: set a composite child with image + label
                            try:
                                hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                                hb.append(img)
                                lbl = Gtk.Label(label=self._label)
                                hb.append(lbl)
                                self._backend_widget.set_child(hb)
                            except Exception:
                                pass
                    except Exception:
                        pass
        except Exception:
            pass
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
            try:
                self._logger.error("_create_backend_widget setup failed", exc_info=True)
            except Exception:
                pass
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
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

    def setIcon(self, icon_name: str):
        """Set/clear the icon for this pushbutton (icon_name may be theme name or path)."""
        try:
            self._icon_name = icon_name
            if getattr(self, "_backend_widget", None) is None:
                return
            img = None
            try:
                img = _resolve_icon(icon_name)
            except Exception:
                img = None
            if img is not None:
                try:
                    try:
                        self._backend_widget.set_icon(img.get_paintable())
                        return
                    except Exception:
                        # Fallback: set composite child with image + label
                        try:
                            hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                            hb.append(img)
                            lbl = Gtk.Label(label=self._label)
                            hb.append(lbl)
                            self._backend_widget.set_child(hb)
                            return
                        except Exception:
                            pass
                except Exception:
                    pass
            # If we reach here, clear any icon and ensure label is present
            try:
                # Reset to simple label-only button
                try:
                    self._backend_widget.set_label(self._label)
                except Exception:
                    try:
                        # If set_label not available, set child to a label
                        lbl = Gtk.Label(label=self._label)
                        self._backend_widget.set_child(lbl)
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            try:
                self._logger.exception("setIcon failed")
            except Exception:
                pass
