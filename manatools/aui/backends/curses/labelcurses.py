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

# Module-level logger for label curses backend
_mod_logger = logging.getLogger("manatools.aui.curses.label.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)


class YLabelCurses(YWidget):
    def __init__(self, parent=None, text="", isHeading=False, isOutputField=False):
        super().__init__(parent)
        self._text = text
        self._is_heading = isHeading
        self._is_output_field = isOutputField
        self._height = 1
        self._focused = False
        self._can_focus = False  # Labels don't get focus
        # per-instance logger
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        self._logger.debug("%s.__init__ text=%s heading=%s", self.__class__.__name__, text, isHeading)
    
    def widgetClass(self):
        return "YLabel"
    
    def text(self):
        return self._text
    
    def setText(self, new_text):
        self._text = new_text
    
    def _create_backend_widget(self):
        try:
            self._backend_widget = self
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception as e:
            try:
                self._logger.error("_create_backend_widget error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_create_backend_widget error: %s", e, exc_info=True)

    def _set_backend_enabled(self, enabled):
        """Enable/disable label: labels are not focusable; just keep enabled state for drawing."""
        try:
            # labels don't accept focus; nothing to change except state used by draw
            # draw() will consult self._enabled from base class
            pass
        except Exception:
            pass

    def _draw(self, window, y, x, width, height):
        try:
            attr = 0
            if self._is_heading:
                attr |= curses.A_BOLD
            # dim if disabled
            if not self.isEnabled():
                attr |= curses.A_DIM

            # Truncate text to fit available width
            display_text = self._text[:max(0, width-1)]
            window.addstr(y, x, display_text, attr)
        except curses.error as e:
            try:
                self._logger.error("_draw curses.error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_draw curses.error: %s", e, exc_info=True)
