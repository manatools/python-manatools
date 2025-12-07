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


class YAlignmentCurses(YSingleChildContainerWidget):
    """
    Single-child alignment container for ncurses. It becomes stretchable on the
    requested axes, and positions the child inside its draw area accordingly.
    """
    def __init__(self, parent=None, horAlign: YAlignmentType=YAlignmentType.YAlignUnchanged, vertAlign: YAlignmentType=YAlignmentType.YAlignUnchanged):
        super().__init__(parent)
        self._halign_spec = horAlign
        self._valign_spec = vertAlign
        self._backend_widget = None  # not used by curses
        self._height = 1

    def widgetClass(self):
        return "YAlignment"

    def stretchable(self, dim: YUIDimension):
        ''' Returns the stretchability of the layout box:
          * The layout box is stretchable if the child is stretchable in
          * this dimension or if the child widget has a layout weight in
          * this dimension.
        '''
        if self._child:
            expand = bool(self._child.stretchable(dim))
            weight = bool(self._child.weight(dim))
            if expand or weight:
                return True
        return False

    def addChild(self, child):
        try:
            super().addChild(child)
        except Exception:
            self._child = child
        # Ensure child is visible to traversal (dialog looks at widget._children)
        try:
            if not hasattr(self, "_children") or self._children is None:
                self._children = []
            if child not in self._children:
                self._children.append(child)
            # keep parent pointer consistent
            try:
                setattr(child, "_parent", self)
            except Exception:
                pass
        except Exception:
            pass

    def setChild(self, child):
        try:
            super().setChild(child)
        except Exception:
            self._child = child
        # Mirror to _children so focus traversal finds it
        try:
            if not hasattr(self, "_children") or self._children is None:
                self._children = []
            # replace existing children with this single child to avoid stale entries
            if self._children != [child]:
                self._children = [child]
            try:
                setattr(child, "_parent", self)
            except Exception:
                pass
        except Exception:
            pass

    def _create_backend_widget(self):
        self._backend_widget = None
        self._height = max(1, getattr(self._child, "_height", 1) if self._child else 1)

    def _set_backend_enabled(self, enabled):
        """Enable/disable alignment container and propagate to its logical child."""
        try:
            # propagate to logical child so it updates its own focusability/state
            child = getattr(self, "_child", None)
            if child is None:
                chs = getattr(self, "_children", None) or []
                child = chs[0] if chs else None
            if child is not None and hasattr(child, "setEnabled"):
                try:
                    child.setEnabled(enabled)
                except Exception:
                    pass
            # nothing else to do for curses backend (no real widget object)
        except Exception:
            pass

    def _child_min_width(self, child, max_width):
        # Heuristic minimal width similar to YHBoxCurses TODO: verify with widget information instead of hardcoded classes
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
        return max(1, min(10, max_width))

    def _draw(self, window, y, x, width, height):
        if not self._child or not hasattr(self._child, "_draw"):
            return
        try:
            # width to give to the child: minimal needed (so it can be pushed)
            ch_min_w = self._child_min_width(self._child, width)
            # Horizontal position
            if self._halign_spec == YAlignmentType.YAlignEnd:
                cx = x + max(0, width - ch_min_w)
            elif self._halign_spec == YAlignmentType.YAlignCenter:
                cx = x + max(0, (width - ch_min_w) // 2)
            else:
                cx = x
            # Vertical position (single line widgets mostly)
            if self._valign_spec == YAlignmentType.YAlignCenter:
                cy = y + max(0, (height - 1) // 2)
            elif self._valign_spec == YAlignmentType.YAlignEnd:
                cy = y + max(0, height - 1)
            else:
                cy = y
            self._child._draw(window, cy, cx, min(ch_min_w, max(1, width)), min(height, getattr(self._child, "_height", 1)))
        except Exception:
            pass
