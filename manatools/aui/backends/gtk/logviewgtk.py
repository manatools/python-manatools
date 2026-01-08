# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.gtk contains all gtk backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
'''
import logging
from gi.repository import Gtk
from ...yui_common import *


class YLogViewGtk(YWidget):
    """GTK backend for YLogView using Gtk.TextView inside Gtk.ScrolledWindow with optional caption label."""
    def __init__(self, parent=None, label: str = "", visibleLines: int = 10, storedLines: int = 0):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        self._label = label or ""
        self._visible = max(1, int(visibleLines or 10))
        self._max_lines = max(0, int(storedLines or 0))
        self._lines = []
        try:
            self.setStretchable(YUIDimension.YD_HORIZ, True)
            self.setStretchable(YUIDimension.YD_VERT, True)
        except Exception:
            pass

    def widgetClass(self):
        return "YLogView"

    def label(self):
        return self._label

    def setLabel(self, label: str):
        self._label = label or ""
        try:
            if getattr(self, "_label_widget", None) is not None:
                self._label_widget.set_text(self._label)
        except Exception:
            self._logger.exception("setLabel failed")

    def visibleLines(self) -> int:
        return int(self._visible)

    def setVisibleLines(self, v: int):
        self._visible = max(1, int(v or 1))
        # Height tuning could be done via CSS or size requests; skip for now.

    def maxLines(self) -> int:
        return int(self._max_lines)

    def setMaxLines(self, m: int):
        self._max_lines = max(0, int(m or 0))
        self._trim_if_needed()
        self._update_display()

    def logText(self) -> str:
        return "\n".join(self._lines)

    def setLogText(self, text: str):
        try:
            raw = [] if text is None else str(text).splitlines()
            self._lines = raw
            self._trim_if_needed()
            self._update_display()
        except Exception:
            self._logger.exception("setLogText failed")

    def lastLine(self) -> str:
        return self._lines[-1] if self._lines else ""

    def appendLines(self, text: str):
        try:
            if text is None:
                return
            for ln in str(text).splitlines():
                self._lines.append(ln)
            self._trim_if_needed()
            self._update_display(scroll_end=True)
        except Exception:
            self._logger.exception("appendLines failed")

    def clearText(self):
        self._lines = []
        self._update_display()

    def lines(self) -> int:
        return len(self._lines)

    # internals
    def _trim_if_needed(self):
        try:
            if self._max_lines > 0 and len(self._lines) > self._max_lines:
                self._lines = self._lines[-self._max_lines:]
        except Exception:
            self._logger.exception("trim failed")

    def _update_display(self, scroll_end: bool = False):
        try:
            if getattr(self, "_buffer", None) is not None:
                self._buffer.set_text("\n".join(self._lines))
                if scroll_end and getattr(self, "_view", None) is not None:
                    try:
                        iter_ = self._buffer.get_end_iter()
                        self._view.scroll_to_iter(iter_, 0.0, False, 0.0, 1.0)
                    except Exception:
                        pass
        except Exception:
            self._logger.exception("update_display failed")

    def _create_backend_widget(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        if self._label:
            lbl = Gtk.Label(label=self._label)
            lbl.set_xalign(0.0)
            self._label_widget = lbl
            box.append(lbl)
        sw = Gtk.ScrolledWindow()
        try:
            sw.set_hexpand(True)
            sw.set_vexpand(True)
        except Exception:
            pass
        tv = Gtk.TextView()
        try:
            tv.set_editable(False)
            tv.set_wrap_mode(Gtk.WrapMode.NONE)
            tv.set_monospace(True)
            tv.set_hexpand(True)
            tv.set_vexpand(True)
        except Exception:
            pass
        # approximate min height from visible lines so it appears with some space
        try:
            line_px = 18
            sw.set_min_content_height(line_px * max(1, int(self._visible)))
        except Exception:
            pass
        buf = tv.get_buffer()
        self._buffer = buf
        self._view = tv
        sw.set_child(tv)
        box.append(sw)
        self._backend_widget = box
        self._update_display()
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        try:
            if getattr(self, "_view", None) is not None:
                self._view.set_sensitive(bool(enabled))
            if getattr(self, "_label_widget", None) is not None:
                self._label_widget.set_sensitive(bool(enabled))
        except Exception:
            pass
