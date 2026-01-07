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
from .commoncurses import pixels_to_chars

# Module-level logger for curses alignment backend
_mod_logger = logging.getLogger("manatools.aui.curses.alignment.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)


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
        self._min_width_px = 0
        self._min_height_px = 0
        # per-instance logger
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        self._logger.debug("%s.__init__ halign=%s valign=%s", self.__class__.__name__, horAlign, vertAlign)
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
        try:
            # for curses we don't create a real window; associate backend_widget to self
            self._backend_widget = self
            self._height = max(1, getattr(self.child(), "_height", 1) if self.hasChildren() else 1)
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception as e:
            try:
                self._logger.error("_create_backend_widget error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_create_backend_widget error: %s", e, exc_info=True)

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
            # width to give to the child: minimal needed or full width if stretchable
            ch_min_w = self._child_min_width(self.child(), width)
            # honor explicit minimum width in pixels, converting to character cells
            try:
                if getattr(self, '_min_width_px', 0) and self._min_width_px > 0:
                    min_chars = pixels_to_chars(int(self._min_width_px), YUIDimension.YD_HORIZ)
                    ch_min_w = max(ch_min_w, min_chars)
            except Exception:
                pass
            # Horizontal position
            # determine the width we'll give to the child: prefer an
            # explicit child _width (or the child's minimal width), but
            # never exceed the available width
            try:
                child_pref_w = getattr(self.child(), "_width", None)
                # If child is stretchable horizontally or has weight, let it use full width
                is_h_stretch = False
                try:
                    is_h_stretch = bool(self.child().stretchable(YUIDimension.YD_HORIZ)) or bool(self.child().weight(YUIDimension.YD_HORIZ))
                except Exception:
                    is_h_stretch = False
                if is_h_stretch:
                    child_w = width
                else:
                    if child_pref_w is not None:
                        child_w = min(width, max(ch_min_w, int(child_pref_w)))
                    else:
                        child_w = min(width, ch_min_w)
            except Exception:
                child_w = min(width, ch_min_w)

            if self._halign_spec == YAlignmentType.YAlignEnd:
                cx = x + max(0, width - child_w)
            elif self._halign_spec == YAlignmentType.YAlignCenter:
                cx = x + max(0, (width - child_w) // 2)
            else:
                cx = x
            # Vertical position (single line widgets mostly)
            if self._valign_spec == YAlignmentType.YAlignCenter:
                cy = y + max(0, (height - 1) // 2)
            elif self._valign_spec == YAlignmentType.YAlignEnd:
                cy = y + max(0, height - 1)
            else:
                cy = y
            # height to give to the child: prefer full height if stretchable, else min/explicit
            ch_height = getattr(self.child(), "_height", 1)
            try:
                is_v_stretch = bool(self.child().stretchable(YUIDimension.YD_VERT)) or bool(self.child().weight(YUIDimension.YD_VERT))
                if is_v_stretch:
                    ch_height = height
            except Exception:
                pass
            try:
                if getattr(self, '_min_height_px', 0) and self._min_height_px > 0:
                    min_h = pixels_to_chars(int(self._min_height_px), YUIDimension.YD_VERT)
                    ch_height = max(ch_height, min_h)
            except Exception:
                pass
            # give the computed width to the child (at least 1 char)
            final_w = max(1, child_w)
            try:
                self._logger.debug("Alignment draw: child=%s halign=%s valign=%s container=(%d,%d) size=(%d,%d) child_min=%d child_pref=%s child_w=%d cx=%d cy=%d",
                                   self.child().debugLabel() if hasattr(self.child(), 'debugLabel') else '<child>',
                                   self._halign_spec, self._valign_spec,
                                   x, y, width, height,
                                   ch_min_w, getattr(self.child(), '_width', None), final_w, cx, cy)
            except Exception:
                pass
            self.child()._draw(window, cy, cx, final_w, min(height, ch_height))
        except Exception:
            pass

    def setMinWidth(self, width_px: int):
        try:
            self._min_width_px = int(width_px) if width_px is not None else 0
        except Exception:
            self._min_width_px = 0

    def setMinHeight(self, height_px: int):
        try:
            self._min_height_px = int(height_px) if height_px is not None else 0
        except Exception:
            self._min_height_px = 0

    def setMinSize(self, width_px: int, height_px: int):
        self.setMinWidth(width_px)
        self.setMinHeight(height_px)
