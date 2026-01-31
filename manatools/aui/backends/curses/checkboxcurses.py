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

# Module-level logger for curses checkbox backend
_mod_logger = logging.getLogger("manatools.aui.curses.checkbox.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)


class YCheckBoxCurses(YWidget):
    def __init__(self, parent=None, label="", is_checked=False):
        super().__init__(parent)
        self._label = label
        self._is_checked = is_checked
        self._focused = False
        self._can_focus = True
        self._height = 1
        # per-instance logger
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        self._logger.debug("%s.__init__ label=%s checked=%s", self.__class__.__name__, label, is_checked)
    
    def widgetClass(self):
        return "YCheckBox"
    
    def value(self):
        return self._is_checked
    
    def setValue(self, checked):
        self._is_checked = checked

    def isChecked(self):
        '''
            Simplified access to value(): Return 'true' if the CheckBox is checked.        
        '''
        return self.value()

    def setChecked(self, checked: bool = True):
        '''
            Simplified access to setValue(): Set the CheckBox to 'checked' state if 'checked' is true.
        '''
        self.setValue(checked)
    
    def label(self):
        return self._label
    
    def _create_backend_widget(self):
        try:
            # In curses, there's no actual backend widget; associate placeholder to self
            self._backend_widget = self
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception as e:
            try:
                self._logger.error("_create_backend_widget error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_create_backend_widget error: %s", e, exc_info=True)

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
        if self._visible is False:
            return
        try:
            checkbox_symbol = "[X]" if self._is_checked else "[ ]"
            text = f"{checkbox_symbol} {self._label}"
            if len(text) > width:
                text = text[:max(0, width - 1)] + "…"

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
        if not self._focused or not self.isEnabled() or not self.visible():
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

    def setVisible(self, visible: bool = True):
        super().setVisible(visible)
        # in curses backend visibility controls whether widget can receive focus
        self._can_focus = bool(visible)