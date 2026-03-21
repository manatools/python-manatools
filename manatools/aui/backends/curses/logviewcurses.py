# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.curses contains all curses backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.curses
'''
import curses
import logging
from ...yui_common import *


class YLogViewCurses(YWidget):
    """ncurses backend for YLogView: renders a scrollable output-only log area.

    Parameters
    ----------
    parent : YWidget, optional
        Parent widget in the AUI hierarchy.
    label : str
        Optional caption drawn above the text area.
    visibleLines : int
        Minimum number of text rows shown (used as a hint by the layout).
    storedLines : int
        Maximum number of lines retained in memory (0 = unlimited).
    focus : YLogViewFocus
        Scroll-focus policy:

        * ``YLogViewFocus.HEAD`` *(default)* — the scroll offset stays
          where it is when new lines arrive; the user starts at the top.
        * ``YLogViewFocus.TAIL`` — the scroll offset is set to the last
          line on every :meth:`appendLines` call, so the newest content
          is always visible.
    reverse : bool
        When ``True`` the display order is **newest-first**: the line most
        recently appended appears at the *top* of the widget and older
        lines are pushed downward.  ``False`` (default) keeps the natural
        insertion order (oldest at top, newest at bottom).

        In *reverse* mode the scroll offset is *not* auto-adjusted on
        append because the newest line is already at position 0.
    """
    def __init__(self, parent=None, label: str = "", visibleLines: int = 10,
                 storedLines: int = 0, focus: 'YLogViewFocus' = None,
                 reverse: bool = False):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        self._label = label or ""
        self._visible = max(1, int(visibleLines or 10))
        self._max_lines = max(0, int(storedLines or 0))
        self._lines = []
        self._backend_widget = self
        if focus is None:
            focus = YLogViewFocus.HEAD
        self._focus = focus
        self._reverse = bool(reverse)
        self._logger.debug(
            "YLogViewCurses init: focus=%s reverse=%s", self._focus, self._reverse)
        # focus + scrolling state
        self._can_focus = True
        self._focused = False
        self._scroll_y = 0  # top line index
        self._scroll_x = 0  # left column index
        try:
            self.setStretchable(YUIDimension.YD_HORIZ, True)
            self.setStretchable(YUIDimension.YD_VERT, True)
        except Exception:
            pass

    def widgetClass(self):
        return "YLogView"

    def label(self) -> str:
        return self._label

    def setLabel(self, label: str):
        self._label = label or ""

    def visibleLines(self) -> int:
        return int(self._visible)

    def setVisibleLines(self, newVisibleLines: int):
        self._visible = max(1, int(newVisibleLines or 1))

    def maxLines(self) -> int:
        return int(self._max_lines)

    def setMaxLines(self, newMaxLines: int):
        self._max_lines = max(0, int(newMaxLines or 0))
        self._trim_if_needed()

    def logText(self) -> str:
        return "\n".join(self._lines)

    def setLogText(self, text: str):
        try:
            raw = [] if text is None else str(text).splitlines()
            self._lines = raw
            self._trim_if_needed()
        except Exception:
            self._logger.exception("setLogText failed")

    def lastLine(self) -> str:
        return self._lines[-1] if self._lines else ""

    def appendLines(self, text: str):
        """Append one or more lines to the log.

        ``self._lines`` is **always** kept in chronological order (oldest at
        index 0, newest at index ``-1``).  The *reverse* flag only controls
        which physical array index maps to each display row inside
        :meth:`_draw`; it never changes the storage order.

        Automatic scrolling:

        * ``TAIL`` → advance ``_scroll_y`` so that the **bottom** of the
          display is in view (newest line in normal mode, oldest in reverse).
        * ``HEAD`` → no change to ``_scroll_y``.
        """
        try:
            if text is None:
                return
            new_lines = str(text).splitlines()
            self._lines.extend(new_lines)
            self._trim_if_needed()
            if self._focus == YLogViewFocus.TAIL:
                # Set scroll to show the last display row.  _draw will clamp.
                self._scroll_y = max(0, len(self._lines) - self._visible)
                self._logger.debug(
                    "appendLines(TAIL): appended %d line(s), scroll_y=%d",
                    len(new_lines), self._scroll_y)
            else:
                self._logger.debug(
                    "appendLines(HEAD): appended %d line(s), scroll_y unchanged",
                    len(new_lines))
        except Exception:
            self._logger.exception("appendLines failed")

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
        """Toggle newest-first display order.

        Only the *display* direction is changed; ``self._lines`` is always
        kept in chronological order and is never mutated here.  The scroll
        offset is reset to 0 so the top of the new view is shown.
        """
        self._reverse = bool(reverse)
        self._logger.debug("setReverse: %s", self._reverse)
        self._scroll_y = 0

    def clearText(self):
        self._lines = []
        self._scroll_y = 0
        self._scroll_x = 0

    def lines(self) -> int:
        return len(self._lines)

    # internals
    def _trim_if_needed(self):
        try:
            if self._max_lines > 0 and len(self._lines) > self._max_lines:
                self._lines = self._lines[-self._max_lines:]
        except Exception:
            self._logger.exception("trim failed")

    # curses drawing
    def _draw(self, window, y, x, width, height):
        if self._visible is False:
            return
        try:
            line = y
            # label
            label_to_show = self._label if self._label else (self.debugLabel() if hasattr(self, 'debugLabel') else "")
            if label_to_show:
                try:
                    window.addstr(line, x, label_to_show[:max(0, width)])
                except curses.error:
                    pass
                line += 1

            # compute content area reserving space for scrollbars if needed
            total_lines = len(self._lines)
            max_len = 0
            try:
                max_len = max((len(s) for s in self._lines)) if self._lines else 0
            except Exception:
                max_len = 0

            content_h = max(0, height - (line - y))
            need_hbar = max_len > width and content_h > 1
            need_vbar = total_lines > content_h

            # reserve one row/col for scrollbars if needed
            if need_hbar:
                content_h -= 1
            content_w = width - (1 if need_vbar else 0)
            if content_h <= 0 or content_w <= 0:
                return

            # clamp scroll offsets
            max_scroll_y = max(0, total_lines - content_h)
            if self._scroll_y > max_scroll_y:
                self._scroll_y = max_scroll_y
            if self._scroll_y < 0:
                self._scroll_y = 0
            max_scroll_x = max(0, max_len - content_w)
            if self._scroll_x > max_scroll_x:
                self._scroll_x = max_scroll_x
            if self._scroll_x < 0:
                self._scroll_x = 0
            # remember viewport for key handling
            self._last_height = content_h
            self._last_width = content_w

            # draw visible lines with horizontal scroll
            for i in range(content_h):
                # In reverse mode the top display row maps to the newest line
                # (_lines[-1]) and the bottom row to the oldest (_lines[0]).
                # _scroll_y always counts from the "top of the virtual display".
                if self._reverse:
                    idx = total_lines - 1 - (self._scroll_y + i)
                else:
                    idx = self._scroll_y + i
                s = self._lines[idx] if 0 <= idx < total_lines else ""
                try:
                    window.addstr(line + i, x, (s[self._scroll_x:self._scroll_x + content_w]).ljust(content_w))
                except curses.error:
                    pass

            # draw vertical scrollbar
            if need_vbar:
                bar_x = x + content_w
                # track
                for i in range(content_h):
                    try:
                        window.addstr(line + i, bar_x, "│")
                    except curses.error:
                        pass
                # thumb size and position
                thumb_h = max(1, int(content_h * content_h / max(1, total_lines)))
                thumb_y = line + int(self._scroll_y * content_h / max(1, total_lines))
                for i in range(thumb_h):
                    if thumb_y + i < line + content_h:
                        try:
                            window.addstr(thumb_y + i, bar_x, "█")
                        except curses.error:
                            pass

            # draw horizontal scrollbar
            if need_hbar:
                bar_y = line + content_h
                # track
                try:
                    window.addstr(bar_y, x, "─" * content_w)
                except curses.error:
                    pass
                thumb_w = max(1, int(content_w * content_w / max(1, max_len)))
                thumb_x = x + int(self._scroll_x * content_w / max(1, max_len))
                for i in range(thumb_w):
                    if thumb_x + i < x + content_w:
                        try:
                            window.addstr(bar_y, thumb_x + i, "█")
                        except curses.error:
                            pass
        except curses.error:
            pass

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled() or not self.visible():
            return False

        handled = True
        # Estimate viewport for scrolling steps; if no layout info, choose 5
        view_h = getattr(self, "_last_height", 5) or 5
        view_w = getattr(self, "_last_width", 10) or 10

        if key in (curses.KEY_UP, ord('k')):
            self._scroll_y = max(0, self._scroll_y - 1)
        elif key in (curses.KEY_DOWN, ord('j')):
            self._scroll_y = self._scroll_y + 1
        elif key == curses.KEY_PPAGE:
            self._scroll_y = max(0, self._scroll_y - max(1, view_h - 1))
        elif key == curses.KEY_NPAGE:
            self._scroll_y = self._scroll_y + max(1, view_h - 1)
        elif key == curses.KEY_HOME:
            self._scroll_y = 0
        elif key == curses.KEY_END:
            # will be clamped in draw
            self._scroll_y = 1 << 30
        elif key in (curses.KEY_LEFT, ord('h')):
            self._scroll_x = max(0, self._scroll_x - 1)
        elif key in (curses.KEY_RIGHT, ord('l')):
            self._scroll_x = self._scroll_x + 1
        else:
            handled = False

        return handled

    def _set_backend_enabled(self, enabled):
        pass

    def setVisible(self, visible: bool = True):
        super().setVisible(visible)
        # in curses backend visibility controls whether widget can receive focus
        self._can_focus = bool(visible)