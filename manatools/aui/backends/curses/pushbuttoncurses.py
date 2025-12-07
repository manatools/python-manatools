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


class YPushButtonCurses(YWidget):
    def __init__(self, parent=None, label=""):
        super().__init__(parent)
        self._label = label
        self._focused = False
        self._can_focus = True
        self._height = 1  # Fixed height - buttons are always one line
    
    def widgetClass(self):
        return "YPushButton"
    
    def label(self):
        return self._label
    
    def setLabel(self, label):
        self._label = label
    
    def _create_backend_widget(self):
        self._backend_widget = None

    def _set_backend_enabled(self, enabled):
        """Enable/disable push button: update focusability and collapse focus if disabling."""
        try:
            if not hasattr(self, "_saved_can_focus"):
                self._saved_can_focus = getattr(self, "_can_focus", True)
            if not enabled:
                try:
                    self._saved_can_focus = self._can_focus
                except Exception:
                    self._saved_can_focus = True
                self._can_focus = False
                if getattr(self, "_focused", False):
                    self._focused = False
            else:
                try:
                    self._can_focus = bool(getattr(self, "_saved_can_focus", True))
                except Exception:
                    self._can_focus = True
        except Exception:
            pass

    def _draw(self, window, y, x, width, height):
        try:
            # Center the button label within available width
            button_text = f"[ {self._label} ]"
            text_x = x + max(0, (width - len(button_text)) // 2)

            # Only draw if we have enough space
            if text_x + len(button_text) <= x + width:
                if not self.isEnabled():
                    attr = curses.A_DIM
                else:
                    attr = curses.A_REVERSE if self._focused else curses.A_NORMAL
                    if self._focused:
                        attr |= curses.A_BOLD

                window.addstr(y, text_x, button_text, attr)
        except curses.error:
            pass

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled():
            return False

        if key == ord('\n') or key == ord(' '):
            # Button pressed -> post widget event to containing dialog
            dlg = self.findDialog()
            if dlg is not None:
                try:
                    dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
                except Exception:
                    pass
            return True
        return False
