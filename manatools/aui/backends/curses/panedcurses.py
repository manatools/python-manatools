# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.curses contains curses backend for YMultiLineEdit

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.curses

YPanedCurses: Curses Paned widget.

- Splits area horizontally or vertically into up to two panes.
- Draws only visible children; hidden ones are not drawn and do not receive keys.
- Special keys when a child has focus:
  '+' => make focused child visible
  '-' => make focused child invisible
- Hidden children remain focus-reachable via parent navigation so '+' can restore visibility.
'''

import curses
import logging
from ...yui_common import YWidget, YUIDimension
from .commoncurses import _curses_recursive_min_height

class YPanedCurses(YWidget):
    """
    ncurses implementation of YPaned with two child panes.
    """

    def __init__(self, parent=None, dimension: YUIDimension = YUIDimension.YD_HORIZ):
        super().__init__(parent)
        self._logger = logging.getLogger("manatools.aui.curses.YPanedCurses")
        self._orientation = dimension
        self._backend_widget = self  # self-managed drawing        
        self._hidden = [False, False]  # visibility flags per child index
        # Minimum height will be computed from children
        self._height = 1
        self._logger.debug("YPanedCurses created orientation=%s", "H" if dimension == YUIDimension.YD_HORIZ else "V")

    def widgetClass(self):
        return "YPaned"

    def _create_backend_widget(self):
        """
        No external backend widget required; drawing is managed in _draw.
        """
        self._backend_widget = self
        self._logger.debug("_create_backend_widget: using self-managed backend")

    def _recompute_min_height(self):
        """Compute minimal height for this horizontal box as the tallest child's minimum."""
        try:
            if not self._children:
                self._height = 1
                return
            self._height = max(1, max(_curses_recursive_min_height(c) for c in self._children))
        except Exception:
            self._height = 1

    def addChild(self, child):
        """
        Add a child to the paned container. First child is 'start', second is 'end'.
        """
        if len(self._children) == 2:
            self._logger.warning("YPanedGtk can only manage two children; ignoring extra child")
            return
        super().addChild(child)
        self._recompute_min_height()
        self._logger.debug("Added start child: %s", getattr(child, "debugLabel", lambda: repr(child))())

    def setStartChild(self, child: YWidget):
        """Explicitly set the start child."""
        try:
            self._children[0] = child
            self._hidden[0] = False
            self._logger.debug("setStartChild: %s", getattr(child, "debugLabel", lambda: repr(child))())
        except Exception as e:
            self._logger.error("setStartChild error: %s", e, exc_info=True)

    def setEndChild(self, child: YWidget):
        """Explicitly set the end child."""
        try:
            self._children[1] = child
            self._hidden[1] = False
            self._logger.debug("setEndChild: %s", getattr(child, "debugLabel", lambda: repr(child))())
        except Exception as e:
            self._logger.error("setEndChild error: %s", e, exc_info=True)

    def _get_focused_child_index(self):
        """
        Try to detect which child currently has focus. Fallback to first present child.
        """
        try:
            for idx, ch in enumerate(self._children):
                if ch is None:
                    continue
                # Heuristic focus detection compatible with existing widgets
                if hasattr(ch, "hasFocus") and callable(getattr(ch, "hasFocus")):
                    if ch.hasFocus():  # type: ignore[attr-defined]
                        return idx
                elif getattr(ch, "_focused", False):
                    return idx
        except Exception as e:
            self._logger.debug("focus detection failed: %s", e)
        # fallback
        return 0 if self._children[0] is not None else 1

    def _set_child_visible(self, idx: int, visible: bool):
        """
        Toggle child visibility without touching the child's own setVisible(),
        so it stays focus-reachable even when hidden.
        """
        try:
            if idx not in (0, 1):
                return
            if self._children[idx] is None:
                return
            self._hidden[idx] = not bool(visible)
            self._logger.debug("Child %d visibility -> %s", idx, "visible" if visible else "hidden")
        except Exception as e:
            self._logger.error("_set_child_visible error: %s", e, exc_info=True)

    def _draw(self, window, y, x, width, height):
        """
        Draw visible children split by orientation.
        - If both visible: split area evenly.
        - If one visible: give full area to that child.
        - Hidden children are not drawn.
        """
        try:
            start, end = self._children
            start_vis = (start is not None) and (not self._hidden[0])
            end_vis = (end is not None) and (not self._hidden[1])

            # If neither is visible, fill with spaces and return
            if not start_vis and not end_vis:
                try:
                    for r in range(max(0, height)):
                        window.addstr(y + r, x, " " * max(0, width))
                except curses.error:
                    pass
                return

            if self._orientation == YUIDimension.YD_HORIZ:
                # horizontal split: left | right
                if start_vis and end_vis:
                    w1 = max(0, width // 2)
                    w2 = max(0, width - w1)
                    if start is not None:
                        start._draw(window, y, x, w1, height)
                    if end is not None:
                        end._draw(window, y, x + w1, w2, height)
                elif start_vis:
                    if start is not None:
                        start._draw(window, y, x, width, height)
                else:
                    if end is not None:
                        end._draw(window, y, x, width, height)
            else:
                # vertical split: top / bottom
                if start_vis and end_vis:
                    h1 = max(0, height // 2)
                    h2 = max(0, height - h1)
                    if start is not None:
                        start._draw(window, y, x, width, h1)
                    if end is not None:
                        end._draw(window, y + h1, x, width, h2)
                elif start_vis:
                    if start is not None:
                        start._draw(window, y, x, width, height)
                else:
                    if end is not None:
                        end._draw(window, y, x, width, height)
        except Exception as e:
            try:
                self._logger.error("_draw error: %s", e, exc_info=True)
            except Exception:
                pass

    def _handle_key(self, key):
        """
        Intercept '+' and '-' to toggle visibility of the focused child.
        - '+' makes focused child visible.
        - '-' makes focused child hidden.
        Hidden child does not receive keys until made visible again.
        """
        try:
            idx = self._get_focused_child_index()
            child = self._children[idx]
            if key in (ord('+'),):
                self._set_child_visible(idx, True)
                return True
            if key in (ord('-'),):
                self._set_child_visible(idx, False)
                return True

            # Delegate key handling to focused child only if visible
            if child is not None and not self._hidden[idx]:
                if hasattr(child, "_handle_key"):
                    try:
                        return bool(child._handle_key(key))  # type: ignore[attr-defined]
                    except Exception as e:
                        self._logger.error("child _handle_key error: %s", e, exc_info=True)
                        return False
            # If hidden (or no child), do not handle other keys
            return False
        except Exception as e:
            self._logger.error("_handle_key error: %s", e, exc_info=True)
            return False
