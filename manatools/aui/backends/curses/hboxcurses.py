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

class YHBoxCurses(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Minimum height will be computed from children
        self._height = 1
    
    def widgetClass(self):
        return "YHBox"
    
    def _create_backend_widget(self):
        self._backend_widget = None

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
        """Ensure internal children list and recompute minimal height."""
        try:
            super().addChild(child)
        except Exception:
            try:
                if not hasattr(self, "_children") or self._children is None:
                    self._children = []
                self._children.append(child)
                child._parent = self
            except Exception:
                pass
        self._recompute_min_height()

    def _set_backend_enabled(self, enabled):
        """Enable/disable HBox and propagate to logical children."""
        try:
            for c in list(getattr(self, "_children", []) or []):
                try:
                    c.setEnabled(enabled)
                except Exception:
                    pass
        except Exception:
            pass

    # Returns the stretchability of the layout box:
    #  * The layout box is stretchable if one of the children is stretchable in
    #  * this dimension or if one of the child widgets has a layout weight in
    #  * this dimension.
    def stretchable(self, dim):
        for child in self._children:
            widget = child.get_backend_widget()
            expand = bool(child.stretchable(dim))
            weight = bool(child.weight(dim))
            if expand or weight:
                return True
        # No child is stretchable in this dimension
        return False

    def _child_min_width(self, child, max_width):
        # Best-effort minimal width heuristic
        try:
            if hasattr(child, "minWidth"):
                return min(max_width, max(1, int(child.minWidth())))
        except Exception:
            pass
        # Heuristics based on common attributes
        try:
            cls = child.widgetClass() if hasattr(child, "widgetClass") else ""
            if cls in ("YLabel", "YPushButton", "YCheckBox"):
                text = getattr(child, "_text", None)
                if text is None:
                    text = getattr(child, "_label", "")
                pad = 4 if cls == "YPushButton" else 0
                return min(max_width, max(1, len(str(text)) + pad))
        except Exception:
            pass
        return max(1, min(10, max_width))  # safe default

    def _draw(self, window, y, x, width, height):
        # Ensure minimal height reflects children so the parent allocated enough rows
        self._recompute_min_height()
        num_children = len(self._children)
        if num_children == 0 or width <= 0 or height <= 0:
            return

        spacing = max(0, num_children - 1)
        available = max(0, width - spacing)

        widths = [0] * num_children
        stretchables = []
        fixed_total = 0
        for i, child in enumerate(self._children):
            if child.stretchable(YUIDimension.YD_HORIZ):
                stretchables.append(i)
            else:
                w = self._child_min_width(child, available)
                widths[i] = w
                fixed_total += w

        remaining = max(0, available - fixed_total)
        if stretchables:
            per = remaining // len(stretchables)
            extra = remaining % len(stretchables)
            for k, idx in enumerate(stretchables):
                widths[idx] = max(1, per + (1 if k < extra else 0))
        else:
            if fixed_total < available:
                leftover = available - fixed_total
                per = leftover // num_children
                extra = leftover % num_children
                for i in range(num_children):
                    base = widths[i] if widths[i] else 1
                    widths[i] = base + per + (1 if i < extra else 0)

        # Draw children and pass full container height to stretchable children
        cx = x
        for i, child in enumerate(self._children):
            w = widths[i]
            if w <= 0:
                continue
            # Give full container height to vertically-stretchable children
            # and to nested VBoxes so their internal layout can use the
            # available vertical space. Otherwise fall back to the child's
            # declared minimal height.
            try:
                cls = child.widgetClass() if hasattr(child, "widgetClass") else ""
            except Exception:
                cls = ""
            if child.stretchable(YUIDimension.YD_VERT) or cls == "YVBox":
                ch = height
            else:
                ch = min(height, max(1, getattr(child, "_height", 1)))
            if hasattr(child, "_draw"):
                child._draw(window, y, cx, w, ch)
            cx += w
            if i < num_children - 1:
                cx += 1
