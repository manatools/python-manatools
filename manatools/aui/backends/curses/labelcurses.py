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
import textwrap
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
        self._auto_wrap = False
        self._height = 1
        self._focused = False
        self._can_focus = False  # Labels don't get focus
        self.setStretchable(YUIDimension.YD_HORIZ, False)
        self.setStretchable(YUIDimension.YD_VERT, False)
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
    
    def isHeading(self) -> bool:
        return bool(self._is_heading)
    
    def isOutputField(self) -> bool:
        return bool(self._is_output_field)
    
    def label(self):
        return self.text()
    
    def value(self):
        return self.text()

    def setText(self, new_text):
        self._text = new_text
    
    def setValue(self, newValue):
        self.setText(newValue)

    def setLabel(self, newLabel):
        self.setText(newLabel)

    def autoWrap(self) -> bool:
        return bool(self._auto_wrap)

    def setAutoWrap(self, on: bool = True):
        self._auto_wrap = bool(on)
        # no backend widget; wrapping handled in _draw
        # update cached minimal height for simple cases (explicit newlines)
        try:
            if not self._auto_wrap:
                self._height = max(1, len(self._text.splitlines()) if "\n" in self._text else 1)
        except Exception:
            pass

    def _desired_height_for_width(self, width: int) -> int:
        """Return desired height in rows for given width, considering wrapping/newlines."""
        try:
            if width <= 1:
                return 1
            if self._auto_wrap:
                total = 0
                paragraphs = self._text.splitlines() if self._text is not None else [""]
                if not paragraphs:
                    paragraphs = [""]
                for para in paragraphs:
                    if para == "":
                        total += 1
                    else:
                        wrapped = textwrap.wrap(para, width=max(1, width), break_long_words=True, break_on_hyphens=False) or [""]
                        total += len(wrapped)
                return max(1, total)
            else:
                if "\n" in (self._text or ""):
                    return max(1, len(self._text.splitlines()))
                return 1
        except Exception:
            return max(1, getattr(self, "_height", 1))
    
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
        if self._visible is False:
            return
        try:
            attr = 0
            if self._is_heading:
                attr |= curses.A_BOLD
            # dim if disabled
            if not self.isEnabled():
                attr |= curses.A_DIM
            if width > 1:
                # Build lines to draw. Respect explicit newlines and wrap paragraphs.
                lines = []
                if self._auto_wrap:
                    # Wrap each paragraph independently (preserve blank lines)
                    for para in self._text.splitlines():
                        if para == "":
                            lines.append("")
                        else:
                            wrapped_para = textwrap.wrap(para, width=max(1, width), break_long_words=True, break_on_hyphens=False) or [""]
                            lines.extend(wrapped_para)
                else:
                    # No auto-wrap: respect explicit newlines but do not reflow paragraphs
                    if "\n" in self._text:
                        lines = self._text.splitlines()
                    else:
                        lines = [self._text]

                # Draw only up to available height
                max_lines = max(1, height)
                for i, line in enumerate(lines[:max_lines]):
                    try:
                        window.addstr(y + i, x, line[:max(0, width)], attr)
                    except curses.error:
                        pass
        except curses.error as e:
            try:
                self._logger.error("_draw curses.error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_draw curses.error: %s", e, exc_info=True)

