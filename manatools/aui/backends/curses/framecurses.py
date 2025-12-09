# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.curses contains all curses backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.curses
'''
import curses
import curses.ascii
import sys
import os
import time
from ...yui_common import *

from .commoncurses import _curses_recursive_min_height

class YFrameCurses(YSingleChildContainerWidget):
    """
    NCurses implementation of YFrame.
    - Draws a framed box with a title.
    - Hosts a single child inside the frame with inner margins so the child's
      own label does not overlap the frame title.
    - Reports stretchability based on its child.
    """
    def __init__(self, parent=None, label=""):
        super().__init__(parent)
        self._label = label or ""
        self._backend_widget = None
        # Preferred minimal height is computed from child (see _update_min_height)
        self._height = 3
        # inner top padding to separate frame title from child's label
        self._inner_top_padding = 1

    def widgetClass(self):
        return "YFrame"

    def _update_min_height(self):
        """Recompute minimal height: at least 3 rows or child layout min + borders + padding."""
        try:
            child = self.child()
            inner_min = _curses_recursive_min_height(child) if child is not None else 1
            self._height = max(3, 2 + self._inner_top_padding + inner_min)
        except Exception:
            self._height = max(self._height, 3)

    def label(self):
        return self._label

    def setLabel(self, new_label):
        try:
            self._label = str(new_label)
        except Exception:
            self._label = new_label

    def stretchable(self, dim):
        """Frame is stretchable if its child is stretchable or has a weight."""
        try:
            child = self.child()
            if child is None:
                return False
            try:
                if bool(child.stretchable(dim)):
                    return True
            except Exception:
                pass
            try:
                if bool(child.weight(dim)):
                    return True
            except Exception:
                pass
        except Exception:
            pass
        return False

    def _create_backend_widget(self):
        # curses backend does not create a separate widget object for frames;
        # drawing is performed in _draw by the parent container.
        self._backend_widget = None
        # Update minimal height based on the child
        self._update_min_height()

    def _set_backend_enabled(self, enabled):
        """Propagate enabled state to the child."""
        try:
            child = self.child()
            if child is not None and hasattr(child, "setEnabled"):
                try:
                    child.setEnabled(enabled)
                except Exception:
                    pass
        except Exception:
            pass

    def addChild(self, child):
        super().addChild(child)        
        # Update minimal height based on the child
        self._update_min_height()

    def _draw(self, window, y, x, width, height):
        """Draw frame border and title, then draw child inside inner area with margins."""
        try:
            if width <= 0 or height <= 0:
                return
            # Ensure minimal height based on child layout before drawing
            self._update_min_height()
            # Graceful fallback for very small areas
            if height < 3 or width < 4:
                try:
                    if self._label and height >= 1 and width > 2:
                        title = f" {self._label} "
                        title = title[:max(0, width - 2)]
                        window.addstr(y, x, title, curses.A_BOLD)
                except curses.error:
                    pass
                return
            # Choose box characters (prefer ACS if available)
            try:
                hline = curses.ACS_HLINE
                vline = curses.ACS_VLINE
                tl = curses.ACS_ULCORNER
                tr = curses.ACS_URCORNER
                bl = curses.ACS_LLCORNER
                br = curses.ACS_LRCORNER
            except Exception:
                hline = ord('-')
                vline = ord('|')
                tl = ord('+')
                tr = ord('+')
                bl = ord('+')
                br = ord('+')

            # Draw corners and edges
            try:
                window.addch(y, x, tl)
                window.addch(y, x + width - 1, tr)
                window.addch(y + height - 1, x, bl)
                window.addch(y + height - 1, x + width - 1, br)
                for cx in range(x + 1, x + width - 1):
                    window.addch(y, cx, hline)
                    window.addch(y + height - 1, cx, hline)
                for cy in range(y + 1, y + height - 1):
                    window.addch(cy, x, vline)
                    window.addch(cy, x + width - 1, vline)
            except curses.error:
                # best-effort: ignore drawing errors when area is too small
                pass

            # Draw title centered on top border (leave at least one space from corners)
            if self._label:
                try:
                    title = f" {self._label} "
                    max_title_len = max(0, width - 4)
                    if len(title) > max_title_len:
                        title = title[:max(0, max_title_len - 3)] + "..."
                    start_x = x + max(1, (width - len(title)) // 2)
                    # overwrite part of top border with title text
                    window.addstr(y, start_x, title, curses.A_BOLD)
                except curses.error:
                    pass

            # Compute inner content rectangle
            inner_x = x + 1
            inner_y = y + 1
            inner_w = max(0, width - 2)
            inner_h = max(0, height - 2)

            pad_top = min(self._inner_top_padding, max(0, inner_h))
            content_y = inner_y + pad_top
            content_h = max(0, inner_h - pad_top)

            child = self.child()
            if child is None:
                return

            # Clamp content height to at least the child layout minimal height
            needed = _curses_recursive_min_height(child)
            # Do not exceed available area; this only influences the draw area passed down
            content_h = min(max(content_h, needed), inner_h)

            if content_h <= 0 or inner_w <= 0:
                return
            if hasattr(child, "_draw"):
                child._draw(window, content_y, inner_x, inner_w, content_h)
        except Exception:
            pass
