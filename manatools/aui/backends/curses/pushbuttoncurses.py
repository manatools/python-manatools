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

# Module-level logger for pushbutton curses backend
_mod_logger = logging.getLogger("manatools.aui.curses.pushbutton.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)


class YPushButtonCurses(YWidget):
    def __init__(self, parent=None, label=""):
        super().__init__(parent)
        self._label = label
        self._focused = False
        self._can_focus = True
        self._icon_name = None
        self._height = 1  # Fixed height - buttons are always one line
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        self._logger.debug("%s.__init__ label=%s", self.__class__.__name__, label)
    
    def widgetClass(self):
        return "YPushButton"
    
    def label(self):
        return self._label
    
    def setLabel(self, label):
        self._label = label
    
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
        except curses.error as e:
            try:
                self._logger.error("_draw curses.error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_draw curses.error: %s", e, exc_info=True)

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
                    try:
                        self._logger.error("_handle_key post event error", exc_info=True)
                    except Exception:
                        _mod_logger.error("_handle_key post event error", exc_info=True)
            return True
        return False

    def setIcon(self, icon_name: str):
        """Store icon name for curses backend (no graphical icon support)."""
        try:
            self._icon_name = icon_name
        except Exception:
            pass
