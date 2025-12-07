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


class YCheckBoxCurses(YWidget):
    def __init__(self, parent=None, label="", is_checked=False):
        super().__init__(parent)
        self._label = label
        self._is_checked = is_checked
        self._focused = False
        self._can_focus = True
        self._height = 1
    
    def widgetClass(self):
        return "YCheckBox"
    
    def value(self):
        return self._is_checked
    
    def setValue(self, checked):
        self._is_checked = checked
    
    def label(self):
        return self._label
    
    def _create_backend_widget(self):
        # In curses, there's no actual backend widget, just internal state
        pass

    def _set_backend_enabled(self, enabled):
        """Enable/disable checkbox: update focusability and collapse focus if disabling."""
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
            checkbox_symbol = "[X]" if self._is_checked else "[ ]"
            text = f"{checkbox_symbol} {self._label}"
            if len(text) > width:
                text = text[:max(0, width - 3)] + "..."

            if self._focused and self.isEnabled():
                window.attron(curses.A_REVERSE)
            elif not self.isEnabled():
                # indicate disabled with dim attribute
                window.attron(curses.A_DIM)

            window.addstr(y, x, text)

            if self._focused and self.isEnabled():
                window.attroff(curses.A_REVERSE)
            elif not self.isEnabled():
                try:
                    window.attroff(curses.A_DIM)
                except Exception:
                    pass
        except curses.error:
            pass

    def _handle_key(self, key):
        if not self.isEnabled():
            return False
        # Space or Enter to toggle
        if key in (ord(' '), ord('\n'), curses.KEY_ENTER):
            self._toggle()
            return True
        return False
    
    def _toggle(self):
        """Toggle checkbox state and post event"""
        self._is_checked = not self._is_checked
        
        if self.notify():
            # Post a YWidgetEvent to the containing dialog
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
            else:
                print(f"CheckBox toggled (no dialog found): {self._label} = {self._is_checked}")
