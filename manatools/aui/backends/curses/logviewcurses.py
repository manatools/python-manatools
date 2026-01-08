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
    - Stores lines with optional retention limit (storedLines==0 means unlimited).
    - Stretchable horizontally and vertically.
    """
    def __init__(self, parent=None, label: str = "", visibleLines: int = 10, storedLines: int = 0):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        self._label = label or ""
        self._visible = max(1, int(visibleLines or 10))
        self._max_lines = max(0, int(storedLines or 0))
        self._lines = []
        self._backend_widget = self
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
        try:
            if text is None:
                return
            for ln in str(text).splitlines():
                self._lines.append(ln)
            self._trim_if_needed()
        except Exception:
            self._logger.exception("appendLines failed")

    def clearText(self):
        self._lines = []

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
            # remaining height for log
            avail_h = max(0, height - (line - y))
            if avail_h <= 0:
                return
            # pick the last avail_h lines
            to_show = self._lines[-avail_h:]
            start_line = line
            for i in range(avail_h):
                s = to_show[i] if i < len(to_show) else ""
                try:
                    window.addstr(start_line + i, x, s[:max(0, width)])
                except curses.error:
                    pass
        except curses.error:
            pass

    def _set_backend_enabled(self, enabled):
        pass
