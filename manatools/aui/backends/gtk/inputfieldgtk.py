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


class YInputFieldGtk(YWidget):
    def __init__(self, parent=None, label="", password_mode=False):
        super().__init__(parent)
        self._label = label
        self._value = ""
        self._password_mode = password_mode
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
    
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
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        self._lbl = Gtk.Label(label=self._label)
        try:
            if hasattr(self._lbl, "set_xalign"):
                self._lbl.set_xalign(0.0)
        except Exception:
            pass
        try:
            vbox.append(self._lbl)
        except Exception:
            self._logger.error("Failed to append label to vbox, trying add()", exc_info=True)
            vbox.add(self._lbl)
        
        if not self._label:
            self._lbl.set_visible(False)

        entry = Gtk.Entry()
        if self._password_mode:
            try:
                entry.set_visibility(False)
            except Exception:
                pass

        try:
            entry.set_text(self._value)
            entry.connect("changed", self._on_changed)
        except Exception:
            pass

        try:
            vbox.append(entry)
        except Exception:
            self._logger.error("Failed to append entry to vbox, trying add()", exc_info=True)
            vbox.add(entry)

        self._backend_widget = vbox
        self._entry_widget = entry
        try:
            if self._help_text:
                self._backend_widget.set_tooltip_text(self._help_text)
        except Exception:
            self._logger.error("Failed to set tooltip text on backend widget", exc_info=True)
        try:
            self._backend_widget.set_visible(self.visible())
        except Exception:
            self._logger.error("Failed to set backend widget visible", exc_info=True)
        self._backend_widget.set_sensitive(self._enabled)
        try:
            # initial stretch policy
            self._apply_stretch_policy()
        except Exception:
            pass
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass
    
    def _on_changed(self, entry):
        try:
            self._value = entry.get_text()
        except Exception:
            self._value = ""
        # Post ValueChanged
        try:
            dlg = self.findDialog()
            if dlg is not None and self.notify():
                dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
        except Exception:
            pass

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

    def setLabel(self, label):
        self._label = label
        if self._backend_widget is None:
            return
        try:
            if hasattr(self, '_lbl') and self._lbl is not None:
                self._lbl.set_text(str(label))
                if not label:
                    self._lbl.set_visible(False)
                else:
                    self._lbl.set_visible(True)
        except Exception:
            self._logger.error("setLabel failed", exc_info=True)

    def setStretchable(self, dim, new_stretch):
        try:
            super().setStretchable(dim, new_stretch)
        except Exception:
            pass
        try:
            self._apply_stretch_policy()
        except Exception:
            pass

    def _apply_stretch_policy(self):
        """Apply independent hexpand/vexpand and size requests for single-line input."""
        try:
            if self._backend_widget is None:
                return
            horiz = bool(self.stretchable(YUIDimension.YD_HORIZ))
            vert = bool(self.stretchable(YUIDimension.YD_VERT))
            # Expansion flags
            try:
                self._backend_widget.set_hexpand(horiz)
                self._backend_widget.set_vexpand(vert)
                self._entry_widget.set_hexpand(horiz)
                self._entry_widget.set_vexpand(vert)
            except Exception:
                pass

            # Compute char/label sizes via Pango
            try:
                layout = self._entry_widget.create_pango_layout("M")
                char_w, line_h = layout.get_pixel_size()
                if not char_w:
                    char_w = 8
                if not line_h:
                    line_h = 18
            except Exception:
                char_w, line_h = 8, 18
                self._logger.exception("Failed to get entry char size", exc_info=True)
            lbl_h = 0
            try:
                if self._lbl.get_visible():
                    lbl_layout = self._lbl.create_pango_layout("M")
                    _, lbl_h = lbl_layout.get_pixel_size()
                    if not lbl_h:
                        lbl_h = 20
            except Exception:
                self._logger.exception("Failed to get label height", exc_info=True)
            desired_chars = 20
            w_px = int(char_w * desired_chars) + 12
            h_px = int(line_h) + lbl_h + 8

            # Horizontal constraint
            try:
                if not horiz:
                    # Prefer width in characters when available
                    if hasattr(self._entry_widget, 'set_width_chars'):
                        self._entry_widget.set_width_chars(desired_chars)
                    else:
                        self._entry_widget.set_size_request(w_px, -1)
                    self._backend_widget.set_size_request(w_px, -1)
                else:
                    self._backend_widget.set_size_request(-1, -1)
                    self._entry_widget.set_size_request(-1, -1)
            except Exception:
                pass

            # Vertical constraint
            try:
                if not vert:
                    self._backend_widget.set_size_request(-1, h_px)
                else:
                    self._backend_widget.set_size_request(-1, -1)
            except Exception:
                pass
        except Exception:
            pass

    def setVisible(self, visible=True):
        super().setVisible(visible)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.set_visible(visible)
        except Exception:
            self._logger.exception("setVisible failed", exc_info=True)

    def setHelpText(self, help_text: str):
        super().setHelpText(help_text)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.set_tooltip_text(help_text)
        except Exception:
            self._logger.exception("setHelpText failed", exc_info=True)