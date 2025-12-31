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


class YLabelGtk(YWidget):
    def __init__(self, parent=None, text="", isHeading=False, isOutputField=False):
        super().__init__(parent)
        self._text = text
        self._is_heading = isHeading
        self._is_output_field = isOutputField
        self._auto_wrap = False
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
    
    def widgetClass(self):
        return "YLabel"
    
    def text(self):
        return self._text
    
    def isHeading(self) -> bool:
        return bool(self._is_heading)
    
    def isOutputField(self) -> bool:
        return bool(self._is_output_field)
    
    def label(self):
        return self.text()
    
    def value(self):
        return self.text()

    def setText(self, new_text):
        self._text = new_text
        if self._backend_widget:
            try:
                self._backend_widget.set_text(new_text)
            except Exception:
                pass
    
    def setValue(self, newValue):
        self.setText(newValue)

    def setLabel(self, newLabel):
        self.setText(newLabel)

    def autoWrap(self) -> bool:
        return bool(self._auto_wrap)

    def setAutoWrap(self, on: bool = True):
        self._auto_wrap = bool(on)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                if hasattr(self._backend_widget, "set_wrap"):
                    self._backend_widget.set_wrap(self._auto_wrap)
                if hasattr(self._backend_widget, "set_wrap_mode"):
                    try:
                        self._backend_widget.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
                    except Exception:
                        pass
        except Exception:
            pass

    def _create_backend_widget(self):
        self._backend_widget = Gtk.Label(label=self._text)
        try:
            # alignment API in Gtk4 differs; fall back to setting xalign if available
            if hasattr(self._backend_widget, "set_xalign"):
                self._backend_widget.set_xalign(0.0)
        except Exception:
            pass
        try:
            if hasattr(self._backend_widget, "set_wrap"):
                self._backend_widget.set_wrap(bool(self._auto_wrap))
            if hasattr(self._backend_widget, "set_wrap_mode"):
                self._backend_widget.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        except Exception:
            pass
        # Output field: allow text selection like a read-only input
        try:
            if hasattr(self._backend_widget, "set_selectable"):
                self._backend_widget.set_selectable(bool(self._is_output_field))
        except Exception:
            pass
        
        if self._is_heading:
            try:
                markup = f"<b>{self._text}</b>"
                self._backend_widget.set_markup(markup)
            except Exception:
                pass
        self._backend_widget.set_sensitive(self._enabled)
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass
        try:
            # apply initial size policy according to any stretch hints
            self._apply_size_policy()
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        """Enable/disable the label widget backend."""
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass

    def _apply_size_policy(self):
        """Apply `hexpand`/`vexpand` on the Gtk.Label according to model stretchable hints."""
        try:
            horiz = bool(self.stretchable(YUIDimension.YD_HORIZ))
        except Exception:
            horiz = False
        try:
            vert = bool(self.stretchable(YUIDimension.YD_VERT))
        except Exception:
            vert = False
        try:
            if getattr(self, '_backend_widget', None) is not None:
                try:
                    if hasattr(self._backend_widget, 'set_hexpand'):
                        self._backend_widget.set_hexpand(horiz)
                except Exception:
                    pass
                try:
                    if hasattr(self._backend_widget, 'set_vexpand'):
                        self._backend_widget.set_vexpand(vert)
                except Exception:
                    pass
        except Exception:
            pass

    def setStretchable(self, dim, new_stretch):
        try:
            super().setStretchable(dim, new_stretch)
        except Exception:
            pass
        try:
            self._apply_size_policy()
        except Exception:
            pass
