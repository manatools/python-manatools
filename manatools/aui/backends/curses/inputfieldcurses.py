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

# Module-level logger for inputfield curses backend
_mod_logger = logging.getLogger("manatools.aui.curses.inputfield.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)


class YInputFieldCurses(YWidget):
    def __init__(self, parent=None, label="", password_mode=False):
        super().__init__(parent)
        self._label = label
        self._value = ""
        self._password_mode = password_mode
        self._cursor_pos = 0
        self._focused = False
        self._can_focus = True
        # one row for field + optional label row on top
        self._height = 1 + (1 if bool(self._label) else 0)
        # per-instance logger
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        self._logger.debug("%s.__init__ label=%s password_mode=%s", self.__class__.__name__, label, password_mode)
    
    def widgetClass(self):
        return "YInputField"
    
    def value(self):
        return self._value
    
    def setValue(self, text):
        self._value = text
        self._cursor_pos = len(text)
    
    def label(self):
        return self._label
    
    def setLabel(self, label):
        self._label = label
        try:
            self._height = 1 + (1 if bool(self._label) else 0)
        except Exception:
            pass
    
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
        """Enable/disable the input field: affect focusability and focused state."""
        try:
            # Save/restore _can_focus when toggling
            if not hasattr(self, "_saved_can_focus"):
                self._saved_can_focus = getattr(self, "_can_focus", True)
            if not enabled:
                # disable focusable behavior
                try:
                    self._saved_can_focus = self._can_focus
                except Exception:
                    self._saved_can_focus = False
                self._can_focus = False
                # if currently focused, remove focus
                if getattr(self, "_focused", False):
                    self._focused = False
            else:
                # restore previous focusability
                try:
                    self._can_focus = bool(getattr(self, "_saved_can_focus", True))
                except Exception:
                    self._can_focus = True
        except Exception:
            pass

    def _draw(self, window, y, x, width, height):
        try:
            line = y
            # Draw label on its own row above field
            if self._label:
                label_text = str(self._label)
                lbl_attr = curses.A_BOLD if getattr(self, '_is_heading', False) else curses.A_NORMAL
                if not self.isEnabled():
                    lbl_attr |= curses.A_DIM
                window.addstr(line, x, label_text[:max(0, width)], lbl_attr)
                line += 1

            # Effective width respecting horizontal stretch
            desired_w = self.minWidth()
            eff_width = width if self.stretchable(YUIDimension.YD_HORIZ) else min(width, desired_w)
            if eff_width <= 0:
                return

            # Prepare display value
            if self._password_mode and self._value:
                display_value = '*' * len(self._value)
            else:
                display_value = self._value

            # Handle scrolling for long values
            if len(display_value) > eff_width:
                if self._cursor_pos >= eff_width:
                    start_pos = self._cursor_pos - eff_width + 1
                    display_value = display_value[start_pos:start_pos + eff_width]
                else:
                    display_value = display_value[:eff_width]

            # Draw input field background
            if not self.isEnabled():
                attr = curses.A_DIM
            else:
                attr = curses.A_REVERSE if self._focused else curses.A_NORMAL

            field_bg = ' ' * eff_width
            window.addstr(line, x, field_bg, attr)

            # Draw text
            if display_value:
                window.addstr(line, x, display_value, attr)

            # Show cursor if focused and enabled
            if self._focused and self.isEnabled():
                cursor_display_pos = min(self._cursor_pos, eff_width - 1)
                if cursor_display_pos < len(display_value):
                    window.chgat(line, x + cursor_display_pos, 1, curses.A_REVERSE | curses.A_BOLD)
        except curses.error as e:
            try:
                self._logger.error("_draw curses.error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_draw curses.error: %s", e, exc_info=True)

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled():
            return False
            
        handled = True
        
        if key == curses.KEY_BACKSPACE or key == 127 or key == 8:
            if self._cursor_pos > 0:
                self._value = self._value[:self._cursor_pos-1] + self._value[self._cursor_pos:]
                self._cursor_pos -= 1
        elif key == curses.KEY_DC:  # Delete key
            if self._cursor_pos < len(self._value):
                self._value = self._value[:self._cursor_pos] + self._value[self._cursor_pos+1:]
        elif key == curses.KEY_LEFT:
            if self._cursor_pos > 0:
                self._cursor_pos -= 1
        elif key == curses.KEY_RIGHT:
            if self._cursor_pos < len(self._value):
                self._cursor_pos += 1
        elif key == curses.KEY_HOME:
            self._cursor_pos = 0
        elif key == curses.KEY_END:
            self._cursor_pos = len(self._value)
        elif 32 <= key <= 126:  # Printable characters
            self._value = self._value[:self._cursor_pos] + chr(key) + self._value[self._cursor_pos:]
            self._cursor_pos += 1
            # Post ValueChanged immediately
            try:
                dlg = self.findDialog()
                if dlg is not None and self.notify():
                    dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
            except Exception:
                pass
        else:
            handled = False
        
        return handled

    def minWidth(self):
        """Preferred minimal width in columns when not horizontally stretchable."""
        try:
            return 20
        except Exception:
            return 20

    def _desired_height_for_width(self, width: int) -> int:
        try:
            return max(1, 1 + (1 if bool(self._label) else 0))
        except Exception:
            return 1
