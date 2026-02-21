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


class _YLabelMeasure(Gtk.Label):
    """Gtk.Label subclass delegating size measurement to YLabelGtk."""

    def __init__(self, owner, label=""):
        """Initialize the measuring label.

        Args:
            owner: Owning YLabelGtk instance.
            label: Initial label text.
        """
        super().__init__(label=label)
        self._owner = owner

    def do_measure(self, orientation, for_size):
        """GTK4 virtual method for size measurement.

        Args:
            orientation: Gtk.Orientation (HORIZONTAL or VERTICAL)
            for_size: Size in the opposite orientation (-1 if not constrained)

        Returns:
            tuple: (minimum_size, natural_size, minimum_baseline, natural_baseline)
        """
        try:
            return self._owner.do_measure(orientation, for_size)
        except Exception:
            self._owner._logger.exception("Label backend do_measure delegation failed", exc_info=True)
            return (0, 0, -1, -1)


class YLabelGtk(YWidget):
    """GTK4 label widget with heading/output-field options and wrapping."""

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

    def do_measure(self, orientation, for_size):
        """GTK4 virtual method for size measurement.

        Args:
            orientation: Gtk.Orientation (HORIZONTAL or VERTICAL)
            for_size: Size in the opposite orientation (-1 if not constrained)

        Returns:
            tuple: (minimum_size, natural_size, minimum_baseline, natural_baseline)
        """
        widget = getattr(self, "_backend_widget", None)
        if widget is not None:
            try:
                minimum_size, natural_size, minimum_baseline, natural_baseline = Gtk.Label.do_measure(widget, orientation, for_size)
                if orientation == Gtk.Orientation.HORIZONTAL:
                    minimum_baseline = -1
                    natural_baseline = -1
                measured = (minimum_size, natural_size, minimum_baseline, natural_baseline)
                self._logger.debug("Label do_measure orientation=%s for_size=%s -> %s", orientation, for_size, measured)
                return measured
            except Exception:
                self._logger.exception("Label base do_measure failed", exc_info=True)

        text = str(getattr(self, "_text", "") or "")
        line_count = max(1, text.count("\n") + 1)
        longest_line = max((len(line) for line in text.splitlines()), default=len(text))
        if orientation == Gtk.Orientation.HORIZONTAL:
            minimum_size = min(80, max(8, longest_line * 5))
            natural_size = max(minimum_size, longest_line * 8)
        else:
            minimum_size = max(18, line_count * 18)
            natural_size = minimum_size
        self._logger.debug(
            "Label fallback do_measure orientation=%s for_size=%s -> min=%s nat=%s",
            orientation,
            for_size,
            minimum_size,
            natural_size,
        )
        return (minimum_size, natural_size, -1, -1)

    def _create_backend_widget(self):
        """Create backend label and apply visual and sizing policy."""
        self._backend_widget = _YLabelMeasure(self, label=self._text)
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
        if self._help_text:
            try:
                self._backend_widget.set_tooltip_text(self._help_text)
            except Exception:
                self._logger.error("Failed to set tooltip text on backend widget", exc_info=True)
        try:
            self._backend_widget.set_visible(self.visible())
        except Exception:
            self._logger.error("Failed to set backend widget visible", exc_info=True)
        try:
            self._backend_widget.set_sensitive(self._enabled)
        except Exception:
            self._logger.exception("Failed to set sensitivity on backend widget")
        self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())    
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
