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


class YLabelCurses(YWidget):
    def __init__(self, parent=None, text="", isHeading=False, isOutputField=False):
        super().__init__(parent)
        self._text = text
        self._is_heading = isHeading
        self._is_output_field = isOutputField
        self._height = 1
        self._focused = False
        self._can_focus = False  # Labels don't get focus
    
    def widgetClass(self):
        return "YLabel"
    
    def text(self):
        return self._text
    
    def setText(self, new_text):
        self._text = new_text
    
    def _create_backend_widget(self):
        self._backend_widget = None

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
        except curses.error:
            pass
