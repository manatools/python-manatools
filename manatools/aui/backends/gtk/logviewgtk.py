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
    """GTK backend for YLogView using Gtk.TextView inside Gtk.ScrolledWindow
    with an optional caption label.

    Parameters
    ----------
    parent : YWidget, optional
        Parent widget in the AUI hierarchy.
    label : str
        Optional caption drawn above the text area.
    visibleLines : int
        Approximate minimum number of text rows shown (governs minimum
        content height via ``set_min_content_height``).
    storedLines : int
        Maximum number of lines retained in memory (0 = unlimited).
    focus : YLogViewFocus
        Scroll-focus policy:

        * ``YLogViewFocus.HEAD`` *(default)* — viewport stays at the first
          line; :meth:`appendLines` does **not** scroll automatically.
        * ``YLogViewFocus.TAIL`` — viewport follows the last line; every
          call to :meth:`appendLines` scrolls to the bottom so the
          freshest content is always visible.
    reverse : bool
        When ``True`` the display order is **newest-first**: the line most
        recently appended appears at the *top* of the widget and older
        lines are pushed downward.  ``False`` (default) keeps the natural
        insertion order (oldest at top, newest at bottom).
    """
    def __init__(self, parent=None, label: str = "", visibleLines: int = 10,
                 storedLines: int = 0, focus: 'YLogViewFocus' = None,
                 reverse: bool = False):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        self._label = label or ""
        self._visible = max(1, int(visibleLines or 10))
        self._max_lines = max(0, int(storedLines or 0))
        self._lines = []
        if focus is None:
            focus = YLogViewFocus.HEAD
        self._focus = focus
        self._reverse = bool(reverse)
        self._logger.debug(
            "YLogViewGtk init: focus=%s reverse=%s", self._focus, self._reverse)
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

    def focus(self) -> 'YLogViewFocus':
        """Return the current scroll-focus policy."""
        return self._focus

    def setFocus(self, focus: 'YLogViewFocus'):
        """Change the scroll-focus policy at runtime."""
        self._focus = focus
        self._logger.debug("setFocus: %s", focus)

    def reverse(self) -> bool:
        """Return whether newest-first display order is active."""
        return self._reverse

    def setReverse(self, reverse: bool):
        """Toggle newest-first display order and refresh the view.

        Only the *display* direction is changed; ``self._lines`` is always
        kept in chronological order and is never mutated here.
        """
        self._reverse = bool(reverse)
        self._logger.debug("setReverse: %s", self._reverse)
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
        """Append one or more lines to the log.

        ``self._lines`` is **always** kept in chronological order (oldest at
        index 0, newest at index ``-1``).  The *reverse* flag only controls
        how the lines are rendered in :meth:`_update_display`; it never
        changes the storage order.

        Automatic scrolling is controlled by :attr:`_focus`:

        * ``TAIL`` → scroll to the bottom of the rendered text (newest line
          in normal mode, oldest line in reverse mode).
        * ``HEAD`` → no automatic scroll.
        """
        try:
            if text is None:
                return
            new_lines = str(text).splitlines()
            self._lines.extend(new_lines)
            self._trim_if_needed()
            scroll_end = (self._focus == YLogViewFocus.TAIL)
            self._logger.debug(
                "appendLines: added %d line(s), scroll_end=%s", len(new_lines), scroll_end)
            self._update_display(scroll_end=scroll_end)
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
        """Refresh the Gtk.TextBuffer from ``self._lines``.

        ``self._lines`` is always chronological (oldest first).  When
        *reverse* is ``True`` the text is built with
        ``reversed(self._lines)`` so the newest line appears at the **top**
        of the TextView and the oldest at the **bottom**.

        When *scroll_end* is ``True`` the view is scrolled to
        ``get_end_iter()`` — the **end of the rendered text** — regardless
        of *reverse*:

        * **normal order** — end = newest line.
        * **reverse order** — end = oldest line (geometrical mirror of
          HEAD+normal).
        """
        try:
            if getattr(self, "_buffer", None) is not None:
                text = (
                    "\n".join(reversed(self._lines))
                    if self._reverse
                    else "\n".join(self._lines)
                )
                self._buffer.set_text(text)
                if scroll_end and getattr(self, "_view", None) is not None:
                    try:
                        iter_ = self._buffer.get_end_iter()
                        self._view.scroll_to_iter(iter_, 0.0, False, 0.0, 1.0)
                    except Exception:
                        self._logger.debug(
                            "_update_display: scroll_to_iter failed", exc_info=True)
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
        # Respect base stretchable properties
        try:
            horiz = bool(self.stretchable(YUIDimension.YD_HORIZ))
            vert = bool(self.stretchable(YUIDimension.YD_VERT))
            sw.set_hexpand(horiz)
            sw.set_vexpand(vert)
        except Exception:
            pass
        tv = Gtk.TextView()
        try:
            tv.set_editable(False)
            tv.set_wrap_mode(Gtk.WrapMode.NONE)
            tv.set_monospace(True)
            # Respect base stretchable properties
            try:
                horiz = bool(self.stretchable(YUIDimension.YD_HORIZ))
                vert = bool(self.stretchable(YUIDimension.YD_VERT))
                tv.set_hexpand(horiz)
                tv.set_vexpand(vert)
            except Exception:
                pass
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
