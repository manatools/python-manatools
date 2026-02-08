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
from typing import Optional
from ...yui_common import *
from .commongtk import _resolve_icon, _convert_mnemonic_to_gtk


class YPushButtonGtk(YWidget):
    """Gtk4 push button wrapper supporting icons, mnemonics, and default state."""
    def __init__(self, parent=None, label: str="", icon_name: Optional[str]=None, icon_only: Optional[bool]=False):
        super().__init__(parent)
        self._label = _convert_mnemonic_to_gtk(label)
        self._icon_name = icon_name
        self._icon_only = bool(icon_only)
        self._is_default = False
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
    
    def widgetClass(self):
        return "YPushButton"
    
    def label(self):
        return self._label
    
    def setLabel(self, label):
        self._label = _convert_mnemonic_to_gtk(label)
        if self._backend_widget:
            try:
                self._backend_widget.set_label(self._label)
            except Exception:
                pass

    def setDefault(self, default: bool):
        """Mark this push button as the dialog default."""
        self._apply_default_state(bool(default), notify_dialog=True)

    def default(self) -> bool:
        """Return True if this button is currently the default."""
        return bool(getattr(self, "_is_default", False))
    
    def _create_backend_widget(self):
        if self._icon_only:
            self._logger.info(f"Creating icon-only button '{self._label}'")
            self._backend_widget = Gtk.Button()
            self._backend_widget.set_use_underline(True)
            if self._icon_name:
                self._backend_widget.set_icon_name(self._icon_name)
        else:
            self._logger.info(f"Creating button with icon and label '{self._label}'")
            try:
                self._backend_widget = Gtk.Button(label=self._label)
                self._backend_widget.set_use_underline(True)
                hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                if self._icon_name:
                    img = _resolve_icon(self._icon_name)
                    if img is not None:
                        hb.append(img)
                lbl = Gtk.Label(label=self._label, use_underline=True)
                # center contents inside the box so button label appears centered
                try:
                    hb.set_halign(Gtk.Align.CENTER)
                    hb.set_valign(Gtk.Align.CENTER)
                    hb.set_hexpand(False)
                except Exception:
                    pass
                try:
                    lbl.set_halign(Gtk.Align.CENTER)
                except Exception:
                    pass
                hb.append(lbl)
                self._backend_widget.set_child(hb)
            except Exception:
                self._logger.exception("Failed to create button with icon and label", exc_info=True)
                raise RuntimeError("Failed to create button with icon and label")

        if self._help_text:
            try:
                self._backend_widget.set_tooltip_text(self._help_text)
            except Exception:
                self._logger.exception("Failed to set tooltip text", exc_info=True)
        try:
            self._backend_widget.set_visible(self.visible())
        except Exception:
            self._logger.exception("Failed to set widget visibility", exc_info=True)

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
        self._sync_default_visual()
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
            if self._icon_only:
                self._backend_widget.set_icon_name(icon_name)
                return
            # not icon_only: try to set icon + label
            img = None
            try:
                img = _resolve_icon(icon_name)
            except Exception:
                img = None
            if img is not None:
                try:
                    # Set composite child with image + label (centered)
                    try:
                        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                        hb.append(img)
                        lbl = Gtk.Label(label=self._label)
                        try:
                            hb.set_halign(Gtk.Align.CENTER)
                            hb.set_valign(Gtk.Align.CENTER)
                            hb.set_hexpand(False)
                        except Exception:
                            pass
                        try:
                            lbl.set_halign(Gtk.Align.CENTER)
                        except Exception:
                            pass
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
                    self._backend_widget.set_use_underline(True)
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

    def setVisible(self, visible=True):
        super().setVisible(visible)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.set_visible(visible)
                except Exception:
                    self._logger.exception("setVisible failed", exc_info=True)
        except Exception:
            pass

    def setHelpText(self, help_text: str):
        super().setHelpText(help_text)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.set_tooltip_text(help_text)
                except Exception:
                    self._logger.exception("setHelpText failed", exc_info=True)
        except Exception:
            pass

    def _apply_default_state(self, state: bool, notify_dialog: bool):
        """Store default flag and notify parent dialog if requested."""
        desired = bool(state)
        if getattr(self, "_is_default", False) == desired and not notify_dialog:
            return
        dlg = self.findDialog() if notify_dialog else None
        if notify_dialog and dlg is not None:
            try:
                if desired:
                    dlg._register_default_button(self)
                else:
                    dlg._unregister_default_button(self)
            except Exception:
                self._logger.exception("Failed to synchronize default state with dialog")
        self._is_default = desired
        self._sync_default_visual()

    def _sync_default_visual(self):
        """Apply/remove Gtk suggested-action styling for default buttons."""
        widget = getattr(self, "_backend_widget", None)
        if widget is None:
            return
        try:
            if self._is_default:
                widget.add_css_class("suggested-action")
            else:
                widget.remove_css_class("suggested-action")
            return
        except Exception:
            pass
        # Fallback for bindings exposing style_context instead of css helpers
        try:
            ctx = widget.get_style_context()
            if ctx:
                if self._is_default:
                    ctx.add_class("suggested-action")
                else:
                    ctx.remove_class("suggested-action")
        except Exception:
            self._logger.exception("Failed to toggle suggested-action class")
