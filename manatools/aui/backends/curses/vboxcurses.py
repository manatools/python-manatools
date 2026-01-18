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

        # Compute both minimal heights and preferred (requested) heights
        child_min_heights = []
        child_pref_heights = []
        stretchable_indices = []
        stretchable_weights = []
        fixed_height_total = 0

        for i, child in enumerate(self._children):
            if child.visible() is False:
                child_min_heights.append(0)
                child_pref_heights.append(0)
                continue
            # Minimal height (hard lower bound)
            min_h = max(1, _curses_recursive_min_height(child))
            # Preferred/requested height (may be larger than min_h)
            pref_h = min_h
            try:
                # explicit _height attribute may express a preferred size
                if hasattr(child, "_height"):
                    h = int(getattr(child, "_height", pref_h))
                    pref_h = max(pref_h, h)
            except Exception:
                pass
            try:
                if hasattr(child, "_desired_height_for_width"):
                    dh = int(child._desired_height_for_width(width))
                    pref_h = max(pref_h, dh)
            except Exception:
                pass
            child_min_heights.append(min_h)
            child_pref_heights.append(pref_h)

            is_stretch = bool(child.stretchable(YUIDimension.YD_VERT))
            if is_stretch:
                stretchable_indices.append(i)
                try:
                    w = child.weight(YUIDimension.YD_VERT)
                    # normalize weight to 0..100; default 0
                    w = int(w) if w is not None else 0
                except Exception:
                    w = 0
                if w < 0:
                    w = 0
                stretchable_weights.append(w)
            else:
                fixed_height_total += min_h

        # Determine spacing budget and allocate stretch space
        # Compute minimal totals and decide allowed gaps
        min_total = sum(child_min_heights)
        # If even minimal sizes plus spacing don't fit, reduce spacing first
        if min_total + spacing > height:
            spacing_allowed = max(0, height - min_total)
        else:
            spacing_allowed = spacing

        # Preferred total is sum of preferred heights
        pref_total = sum(child_pref_heights)

        # Start allocation from preferred heights clamped to available space
        allocated = list(child_pref_heights)

        # If preferred total plus spacing fits, we'll later distribute surplus
        total_with_pref = pref_total + spacing_allowed
        if total_with_pref <= height:
            surplus = height - total_with_pref
        else:
            surplus = 0

        # If there's surplus after preferred sizes and allowed spacing, distribute
        # it among stretchable children according to their weights (0..100).
        if stretchable_indices and surplus > 0:
            weights = [stretchable_weights[i] for i in range(len(stretchable_indices))]
            total_weight = sum(weights)
            # If all weights are zero, distribute equally
            if total_weight <= 0:
                per = surplus // len(stretchable_indices)
                extra_left = surplus % len(stretchable_indices)
                for k, idx in enumerate(stretchable_indices):
                    allocated[idx] += per + (1 if k < extra_left else 0)
            else:
                # Distribute proportional to weights
                assigned = [0] * len(stretchable_indices)
                base = 0
                for k, idx in enumerate(stretchable_indices):
                    add = (surplus * weights[k]) // total_weight
                    assigned[k] = add
                    base += add
                leftover = surplus - base
                for k in range(len(stretchable_indices)):
                    if leftover <= 0:
                        break
                    assigned[k] += 1
                    leftover -= 1
                for k, idx in enumerate(stretchable_indices):
                    allocated[idx] += assigned[k]

        # If preferred sizes + spacing do not fit, we must shrink from preferred
        # down to minima. Reduce largest available slack first.
        total_alloc = sum(allocated) + spacing_allowed
        if total_alloc > height:
            overflow = total_alloc - height
            # compute how much each child can be reduced (allocated - min)
            reducible = [max(0, allocated[i] - child_min_heights[i]) for i in range(num_children)]
            # sort indices by reducible descending to preserve small widgets
            order = sorted(range(num_children), key=lambda ii: reducible[ii], reverse=True)
            for idx in order:
                if overflow <= 0:
                    break
                can = reducible[idx]
                if can <= 0:
                    continue
                take = min(can, overflow)
                allocated[idx] -= take
                overflow -= take
            # if still overflow, clamp from any child down to 1
            if overflow > 0:
                for i in range(num_children):
                    if overflow <= 0:
                        break
                    can = max(0, allocated[i] - 1)
                    take = min(can, overflow)
                    allocated[i] -= take
                    overflow -= take
            total_alloc = sum(allocated) + spacing_allowed

        # If still room, give remainder to last stretchable/last child
        total_alloc = sum(allocated) + spacing_allowed
        if total_alloc < height:
            extra = height - total_alloc
            target = stretchable_indices[-1] if stretchable_indices else (num_children - 1)
            allocated[target] += extra
        elif total_alloc > height:
            diff = total_alloc - height
            target = stretchable_indices[-1] if stretchable_indices else (num_children - 1)
            allocated[target] = max(1, allocated[target] - diff)

        # Draw children with allocated heights, inserting at most spacing_allowed gaps
        cy = y
        gaps_allowed = spacing_allowed
        for i, child in enumerate(self._children):
            if child.visible() is False:
                continue
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
            # Insert at most one-line gap between children if budget allows
            if i < num_children - 1 and gaps_allowed > 0 and cy < (y + height):
                cy += 1
                gaps_allowed -= 1
