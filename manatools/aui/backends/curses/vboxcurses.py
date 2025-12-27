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
import logging
from ...yui_common import *

from .commoncurses import _curses_recursive_min_height

# Module-level logger for vbox curses backend
_mod_logger = logging.getLogger("manatools.aui.curses.vbox.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)

class YVBoxCurses(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # per-instance logger
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        self._logger.debug("%s.__init__", self.__class__.__name__)
    
    def widgetClass(self):
        return "YVBox"

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

    def _create_backend_widget(self):
        try:
            self._backend_widget = self
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            _mod_logger.error("_create_backend_widget error: %s", e, exc_info=True)

    def _set_backend_enabled(self, enabled):
        """Enable/disable VBox and propagate to logical children."""
        try:
            for c in list(getattr(self, "_children", []) or []):
                try:
                    c.setEnabled(enabled)
                except Exception:
                    try:
                        self._logger.error("_set_backend_enabled child setEnabled error", exc_info=True)
                    except Exception:
                        _mod_logger.error("_set_backend_enabled child setEnabled error", exc_info=True)
        except Exception:
            try:
                self._logger.error("_set_backend_enabled error", exc_info=True)
            except Exception:
                _mod_logger.error("_set_backend_enabled error", exc_info=True)

    def _draw(self, window, y, x, width, height):
        # Vertical layout with spacing; give stretchable children more than their minimum
        num_children = len(self._children)
        if num_children == 0 or height <= 0 or width <= 0:
            return

        spacing = max(0, num_children - 1)

        child_min_heights = []
        stretchable_indices = []
        stretchable_weights = []
        fixed_height_total = 0

        for i, child in enumerate(self._children):
            # Use recursive min height for containers and frames
            child_min = max(1, _curses_recursive_min_height(child))
            # If child can compute desired height for the current width, honor it
            try:
                if hasattr(child, "_desired_height_for_width"):
                    dh = int(child._desired_height_for_width(width))
                    if dh > child_min:
                        child_min = dh
            except Exception:
                pass
            child_min_heights.append(child_min)

            is_stretch = bool(child.stretchable(YUIDimension.YD_VERT))
            if is_stretch:
                stretchable_indices.append(i)
                try:
                    w = child.weight(YUIDimension.YD_VERT)
                    w = int(w) if w is not None else 1
                except Exception:
                    w = 1
                if w <= 0:
                    w = 1
                stretchable_weights.append(w)
            else:
                fixed_height_total += child_min

        available_for_stretch = max(0, height - fixed_height_total - spacing)

        allocated = list(child_min_heights)

        if stretchable_indices:
            total_weight = sum(stretchable_weights) or len(stretchable_indices)
            # Proportional distribution of extra rows
            extras = [0] * len(stretchable_indices)
            base = 0
            for k, idx in enumerate(stretchable_indices):
                extra = (available_for_stretch * stretchable_weights[k]) // total_weight
                extras[k] = extra
                base += extra
            # Distribute leftover rows due to integer division
            leftover = available_for_stretch - base
            for k in range(len(stretchable_indices)):
                if leftover <= 0:
                    break
                extras[k] += 1
                leftover -= 1
            for k, idx in enumerate(stretchable_indices):
                allocated[idx] = child_min_heights[idx] + extras[k]

        total_alloc = sum(allocated) + spacing
        if total_alloc < height:
            # Give remainder to the last stretchable (or last child)
            extra = height - total_alloc
            target = stretchable_indices[-1] if stretchable_indices else (num_children - 1)
            allocated[target] += extra
        elif total_alloc > height:
            # Reduce overflow from the last stretchable (or last child)
            diff = total_alloc - height
            target = stretchable_indices[-1] if stretchable_indices else (num_children - 1)
            allocated[target] = max(1, allocated[target] - diff)

        # Draw children with allocated heights
        cy = y
        for i, child in enumerate(self._children):
            ch = allocated[i]
            if ch <= 0:
                continue
            if cy + ch > y + height:
                ch = max(0, (y + height) - cy)
            if ch <= 0:
                break
            try:
                if hasattr(child, "_draw"):
                    child._draw(window, cy, x, width, ch)
            except Exception:
                try:
                    self._logger.error("_draw child error: %s", child, exc_info=True)
                except Exception:
                    _mod_logger.error("_draw child error", exc_info=True)
            cy += ch
            if i < num_children - 1 and cy < (y + height):
                cy += 1  # one-line spacing
