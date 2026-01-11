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
        # If the child is a container, compute its recursive minimal width
        try:
            cls = child.widgetClass() if hasattr(child, "widgetClass") else ""
            if cls in ("YVBox", "YHBox", "YFrame", "YCheckBoxFrame", "YAlignment", "YReplacePoint"):
                try:
                    return min(max_width, max(1, _curses_recursive_min_width(child)))
                except Exception:
                    pass
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
        pref_reserved = [0] * num_children
        child_weights = [0] * num_children
        for i, child in enumerate(self._children):
            # compute each child's minimal width (best-effort)
            m = self._child_min_width(child, available)
            min_reserved[i] = max(1, m)
            # preferred width: allow explicit _width or min_reserved as default
            try:
                pref_w = int(getattr(child, "_width", min_reserved[i]))
            except Exception:
                pref_w = min_reserved[i]
            pref_reserved[i] = max(min_reserved[i], pref_w)
            # gather declared weight (if any)
            try:
                w = int(child.weight(YUIDimension.YD_HORIZ))
            except Exception:
                try:
                    w = int(getattr(child, "_weight", 0))
                except Exception:
                    w = 0
            if w < 0:
                w = 0
            child_weights[i] = w
            # consider as stretchable if explicitly stretchable or has non-zero weight
            if child.stretchable(YUIDimension.YD_HORIZ) or child_weights[i] > 0:
                stretchables.append(i)

        # Sum fixed (non-stretchable) minimal widths and minimal total for stretchables
        fixed_total = sum(min_reserved[i] for i, c in enumerate(self._children) if not (c.stretchable(YUIDimension.YD_HORIZ) or child_weights[i] > 0))
        min_stretch_total = sum(min_reserved[i] for i, c in enumerate(self._children) if (c.stretchable(YUIDimension.YD_HORIZ) or child_weights[i] > 0))

        # Start allocation from preferred widths, then adjust to fit available
        widths = list(pref_reserved)

        # collect stretchable weights (0 means equal-share fallback)
        stretch_weights = []
        for idx in stretchables:
            w = child_weights[idx] if idx < len(child_weights) else 0
            # normalize weight to 0..100 range if out of bounds
            try:
                if w > 100:
                    w = 100
                elif w < 0:
                    w = 0
            except Exception:
                w = 0
            stretch_weights.append(w)

        try:
            # Detailed per-child diagnostics
            details = []
            for i, child in enumerate(self._children):
                try:
                    lbl = child.debugLabel() if hasattr(child, 'debugLabel') else f'child_{i}'
                except Exception:
                    lbl = f'child_{i}'
                try:
                    sw = bool(child.stretchable(YUIDimension.YD_HORIZ))
                except Exception:
                    sw = False
                try:
                    wv = int(child.weight(YUIDimension.YD_HORIZ))
                except Exception:
                    wv = 0
                details.append((i, lbl, min_reserved[i], pref_reserved[i], sw, wv))
            #self._logger.debug("HBox allocation inputs: available=%d spacing=%d details=%s",
            #                   available, spacing, details)
        except Exception:
            pass

        total_pref = sum(widths)
        # If preferred total fits, distribute surplus among stretchables by weight
        if total_pref <= available:
            surplus = available - total_pref
            if stretchables:
                total_weight = sum(stretch_weights)
                if total_weight <= 0:
                    per = surplus // len(stretchables) if stretchables else 0
                    extra = surplus % len(stretchables) if stretchables else 0
                    for k, idx in enumerate(stretchables):
                        widths[idx] += per + (1 if k < extra else 0)
                else:
                    assigned = [0] * len(stretchables)
                    base = 0
                    for k, w in enumerate(stretch_weights):
                        add = (surplus * w) // total_weight
                        assigned[k] = add
                        base += add
                    leftover = surplus - base
                    for k in range(len(stretchables)):
                        if leftover <= 0:
                            break
                        assigned[k] += 1
                        leftover -= 1
                    for k, idx in enumerate(stretchables):
                        widths[idx] += assigned[k]
            else:
                # No stretchables: spread leftover evenly among all children
                per = surplus // num_children if num_children else 0
                extra = surplus % num_children if num_children else 0
                for i in range(num_children):
                    widths[i] += per + (1 if i < extra else 0)
        else:
            # Need to shrink preferred sizes down to minima to fit available
            total_with_spacing = total_pref
            if total_with_spacing + spacing > available:
                overflow = total_with_spacing + spacing - available
                reducible = [max(0, widths[i] - min_reserved[i]) for i in range(num_children)]
                order = sorted(range(num_children), key=lambda ii: reducible[ii], reverse=True)
                for idx in order:
                    if overflow <= 0:
                        break
                    can = reducible[idx]
                    if can <= 0:
                        continue
                    take = min(can, overflow)
                    widths[idx] -= take
                    overflow -= take
                if overflow > 0:
                    for i in range(num_children):
                        if overflow <= 0:
                            break
                        can = max(0, widths[i] - 1)
                        take = min(can, overflow)
                        widths[i] -= take
                        overflow -= take

        # Final debug of allocated widths
        #self._logger.debug("HBox allocated widths=%s total=%d (available=%d)", widths, sum(widths), available)

        # Ensure containers get at least the width required by their children
        def _required_width_for(widget):
            try:
                cls = widget.widgetClass() if hasattr(widget, 'widgetClass') else ''
            except Exception:
                cls = ''
            try:
                if cls == 'YPushButton':
                    lbl = getattr(widget, '_label', '')
                    return max(1, len(f"[ {lbl} ]"))
                if cls == 'YLabel':
                    txt = getattr(widget, '_text', '') or getattr(widget, '_label', '')
                    return max(1, len(str(txt)))
                if cls in ('YVBox', 'YHBox', 'YFrame', 'YCheckBoxFrame', 'YAlignment', 'YReplacePoint'):
                    # for containers, required width is max of children's required widths
                    mx = 1
                    for ch in getattr(widget, '_children', []) or []:
                        try:
                            r = _required_width_for(ch)
                            if r > mx:
                                mx = r
                        except Exception:
                            pass
                    return mx
            except Exception:
                pass
            # fallback to minimal reserved
            try:
                return max(1, _curses_recursive_min_width(widget))
            except Exception:
                return 1

        # try to satisfy required widths by borrowing from others
        for i, child in enumerate(self._children):
            req = _required_width_for(child)
            if widths[i] < req:
                need = req - widths[i]
                # try to reduce other children that are above their minima
                for j in range(num_children):
                    if j == i:
                        continue
                    avail = widths[j] - min_reserved[j]
                    if avail <= 0:
                        continue
                    take = min(avail, need)
                    widths[j] -= take
                    widths[i] += take
                    need -= take
                    if need <= 0:
                        break
                # if still need, clamp to available overall (best-effort)
                if widths[i] < req:
                    # nothing else we can do; leave as-is
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
                #self._logger.debug("HBox drawing child %d: lbl=%s alloc_w=%d x=%d height=%d ch_h=%d", i,
                #                    (child.debugLabel() if hasattr(child, 'debugLabel') else f'child_{i}'),
                #                    w, cx, height, ch)
                child._draw(window, y, cx, w, ch)
            cx += w
            if i < num_children - 1:
                cx += 1
