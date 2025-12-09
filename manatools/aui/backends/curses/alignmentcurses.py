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
        if self.hasChildren():
            # get the only child
            child = self.child()
            expand = bool(child.stretchable(dim))
            weight = bool(child.weight(dim))
            if expand or weight:
                return True
        return False

    def _create_backend_widget(self):
        self._backend_widget = None  # no real widget for curses
        self._height = max(1, getattr(self.child(), "_height", 1) if self.hasChildren() else 1)

    def _set_backend_enabled(self, enabled):
        """Enable/disable alignment container and propagate to its logical child."""
        try:
            # propagate to logical child so it updates its own focusability/state
            child = self.child()            
            if child is not None:
                child.setEnabled(enabled)
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
        
        if not self.hasChildren() or not hasattr(self.child(), "_draw"):
            return
        try:
            # width to give to the child: minimal needed (so it can be pushed)
            ch_min_w = self._child_min_width(self.child(), width)
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
            self.child()._draw(window, cy, cx, min(ch_min_w, max(1, width)), min(height, getattr(self.child(), "_height", 1)))
        except Exception:
            pass
