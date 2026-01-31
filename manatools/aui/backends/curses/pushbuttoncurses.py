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
from .commoncurses import extract_mnemonic, split_mnemonic

# Module-level logger for pushbutton curses backend
_mod_logger = logging.getLogger("manatools.aui.curses.pushbutton.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)


class YPushButtonCurses(YWidget):
    def __init__(self, parent=None, label: str="", icon_name: Optional[str]=None, icon_only: Optional[bool]=False):
        super().__init__(parent)
        self._label = label
        self._focused = False
        self._can_focus = True
        self._icon_name = icon_name
        self._icon_only = bool(icon_only)
        self._x = 0
        self._y = 0
        self._height = 1  # Fixed height - buttons are always one line
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        # derive mnemonic and cleaned label if present
        try:
            self._mnemonic, self._mnemonic_index, self._clean_label = split_mnemonic(self._label)
        except Exception:
            self._mnemonic, self._mnemonic_index, self._clean_label = None, None, self._label
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
        try:
            self._mnemonic, self._mnemonic_index, self._clean_label = split_mnemonic(self._label)
        except Exception:
            self._mnemonic, self._mnemonic_index, self._clean_label = None, None, self._label
    
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
        if self._visible is False:
            return
        try:
            # Center the button label within available width, show underline for mnemonic
            clean = getattr(self, "_clean_label", None) or self._label
            button_text = f"[ {clean} ]"
            # Determine drawing position and clip text if necessary
            if width <= 0:
                return
            if len(button_text) <= width:
                text_x = x + max(0, (width - len(button_text)) // 2)
                draw_text = button_text
            else:
                # Not enough space: draw truncated centered/left-aligned text
                draw_text = button_text[:max(1, width)]
                text_x = x

            if not self.isEnabled():
                attr = curses.A_DIM
            else:
                attr = curses.A_REVERSE if self._focused else curses.A_NORMAL
                if self._focused:
                    attr |= curses.A_BOLD

            self._x = text_x
            self._y = y

            try:
                window.addstr(y, text_x, draw_text, attr)
                # underline mnemonic if visible
                if self._mnemonic_index is not None:
                    underline_pos = 2 + self._mnemonic_index  # within "[  ]"
                    if 0 <= underline_pos < len(draw_text):
                        try:
                            window.addstr(y, text_x + underline_pos, draw_text[underline_pos], attr | curses.A_UNDERLINE)
                        except curses.error:
                            pass
            except curses.error:
                # Best-effort: if even this fails, ignore
                pass
        except curses.error as e:
            try:
                self._logger.error("_draw curses.error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_draw curses.error: %s", e, exc_info=True)

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled() or not self.visible():
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
        # mnemonic letter activates as well when focused
        try:
            if self._mnemonic:
                if key == ord(self._mnemonic) or key == ord(self._mnemonic.upper()):
                    dlg = self.findDialog()
                    if dlg is not None:
                        try:
                            dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
                        except Exception:
                            pass
                    return True
        except Exception:
            pass
        return False

    def setIcon(self, icon_name: str):
        """Store icon name for curses backend (no graphical icon support)."""
        try:
            self._icon_name = icon_name
        except Exception:
            pass

    def setVisible(self, visible=True):
        super().setVisible(visible)
        self._can_focus = bool(visible)