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

# Module-level logger for hbox curses backend
_mod_logger = logging.getLogger("manatools.aui.curses.hbox.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)

class YHBoxCurses(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Minimum height will be computed from children
        self._height = 1
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        self._logger.debug("%s.__init__", self.__class__.__name__)
    
    def widgetClass(self):
        return "YHBox"
    
    def _create_backend_widget(self):
        try:
            # No real curses widget; associate placeholder to self
            self._backend_widget = self
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception as e:
            try:
                self._logger.error("_create_backend_widget error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_create_backend_widget error: %s", e, exc_info=True)

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
                pad = 4 if cls in ("YPushButton", "YCheckBox") else 0
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

        # Compute a safe minimal reservation for every child so that
        # stretchable spacers cannot steal the minimum space required
        # by subsequent fixed widgets (e.g. the final checkbox).
        widths = [0] * num_children
        stretchables = []
        min_reserved = [0] * num_children
        for i, child in enumerate(self._children):
            # compute each child's minimal width (best-effort)
            m = self._child_min_width(child, available)
            min_reserved[i] = max(1, m)
            if child.stretchable(YUIDimension.YD_HORIZ):
                stretchables.append(i)

        # Sum fixed (non-stretchable) minimal widths and minimal total for stretchables
        fixed_total = sum(min_reserved[i] for i, c in enumerate(self._children) if not c.stretchable(YUIDimension.YD_HORIZ))
        min_stretch_total = sum(min_reserved[i] for i, c in enumerate(self._children) if c.stretchable(YUIDimension.YD_HORIZ))

        # Available space already accounts for gaps
        remaining = available - fixed_total - min_stretch_total

        if stretchables and remaining > 0:
            # Start from each stretchable's minimum, then distribute leftover
            per = remaining // len(stretchables)
            extra = remaining % len(stretchables)
            for k, idx in enumerate(stretchables):
                widths[idx] = min_reserved[idx] + per + (1 if k < extra else 0)
            # Fixed children get their reserved minima
            for i, child in enumerate(self._children):
                if not child.stretchable(YUIDimension.YD_HORIZ):
                    widths[i] = min_reserved[i]
        else:
            # Either no stretchables, or not enough space to give extra.
            # In this case, try to honor minimal reservations as much as possible.
            # If total minima exceed available, shrink proportionally but keep at least 1.
            total_min = fixed_total + min_stretch_total
            if total_min <= available:
                # we have some leftover but no stretchables to expand; distribute among all
                leftover = available - total_min
                per = leftover // num_children if num_children else 0
                extra = leftover % num_children if num_children else 0
                for i in range(num_children):
                    widths[i] = min_reserved[i] + per + (1 if i < extra else 0)
            else:
                # Need to shrink some minima to fit; compute shrink ratio
                # Start from minima and reduce from largest items first to preserve small widgets
                widths = list(min_reserved)
                overflow = total_min - available
                # Sort indices by current width descending
                order = sorted(range(num_children), key=lambda ii: widths[ii], reverse=True)
                for idx in order:
                    if overflow <= 0:
                        break
                    can_reduce = widths[idx] - 1
                    if can_reduce <= 0:
                        continue
                    take = min(can_reduce, overflow)
                    widths[idx] -= take
                    overflow -= take
                # If still overflow (shouldn't happen), clamp all to 1
                if overflow > 0:
                    for i in range(num_children):
                        widths[i] = 1

        # Debug: log final allocation before drawing children
        try:
            total_assigned = sum(widths)
            self._logger.info("HBox final widths=%s total=%d (available=%d)", widths, total_assigned, available)
            self._logger.debug("HBox internal min_reserved=%s fixed_total=%d min_stretch_total=%d num_stretch=%d",
                               min_reserved, fixed_total, min_stretch_total if 'min_stretch_total' in locals() else 0,
                               len(stretchables))
        except Exception:
            pass

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
