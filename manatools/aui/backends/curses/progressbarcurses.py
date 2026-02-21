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

# Module-level logger for progressbar curses backend
_mod_logger = logging.getLogger("manatools.aui.curses.progressbar.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)

class YProgressBarCurses(YWidget):
    def __init__(self, parent=None, label="", maxValue=100):
        super().__init__(parent)
        self._label = label
        self._max_value = int(maxValue) if maxValue is not None else 100
        self._value = 0
        self._x = 0
        self._y = 0
        # progress bar occupies 2 rows when label present, otherwise 1
        self._height = 2 if self._label else 1
        self._backend_widget = None
        #default stretchable in horizontal direction
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        self._logger.debug("%s.__init__ label=%s maxValue=%s", self.__class__.__name__, label, maxValue)

    def widgetClass(self):
        return "YProgressBar"

    def label(self):
        return self._label

    def setLabel(self, newLabel):
        try:
            self._label = str(newLabel)
            # adjust height when label toggles
            try:
                self._height = 2 if self._label else 1
            except Exception:
                pass
            # request immediate redraw of parent dialog if present
            dlg = self.findDialog()
            if dlg is not None:
                try:
                    dlg._last_draw_time = 0
                except Exception:
                    pass
        except Exception:
            pass

    def maxValue(self):
        return int(self._max_value)

    def value(self):
        return int(self._value)

    def setValue(self, newValue):
        try:
            v = int(newValue)
            if v < 0:
                v = 0
            if v > self._max_value:
                v = self._max_value
            self._value = v
            # request immediate redraw of parent dialog
            dlg = self.findDialog()
            if dlg is not None:
                try:
                    dlg._last_draw_time = 0
                except Exception:
                    pass
        except Exception:
            pass

    def _create_backend_widget(self):
        try:
            # associate placeholder backend widget to self
            self._backend_widget = self
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception as e:
            try:
                self._logger.error("_create_backend_widget error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_create_backend_widget error: %s", e, exc_info=True)

    def _draw(self, window, y, x, width, height):
        if self._visible is False:
            return
        try:
            if width <= 0 or height <= 0:
                return

            # Determine where to draw label and bar
            draw_label = bool(self._label)
            label_y = y if draw_label else None
            bar_y = y + (1 if draw_label else 0)

            # Draw label (single line) above the bar
            if draw_label and label_y is not None and width > 0:
                try:
                    attr = 0
                    if not self.isEnabled():
                        attr |= curses.A_DIM
                    text = str(self._label)[:max(0, width)]
                    window.addstr(label_y, x, text, attr)
                except curses.error:
                    pass

            # Draw progress bar line
            try:
                # Compute fill fraction and percent text
                maxv = max(1, int(self._max_value))
                val = max(0, int(self._value))
                frac = float(val) / float(maxv)
                fill = int(frac * width)

                # Bar characters
                filled_char = '='
                empty_char = ' '
                bar_str = (filled_char * fill) + (empty_char * max(0, width - fill))

                # Center percentage text
                perc = int(frac * 100)
                perc_text = f"{perc}%"
                pt_len = len(perc_text)
                pt_x = x + max(0, (width - pt_len) // 2)

                # Attrs
                bar_attr = curses.A_REVERSE if self.isEnabled() else curses.A_DIM
                perc_attr = curses.A_BOLD if self.isEnabled() else curses.A_DIM

                # Tooltip positioning
                self._x = x
                self._y = bar_y
                # Draw base bar
                try:
                    window.addstr(bar_y, x, bar_str[:width], bar_attr)
                except curses.error:
                    pass

                # Overlay percentage text
                try:
                    # Ensure percentage fits inside bar
                    if pt_x + pt_len <= x + width:
                        window.addstr(bar_y, pt_x, perc_text, perc_attr)
                except curses.error:
                    pass
            except Exception:
                pass
        except Exception as e:
            try:
                self._logger.error("_draw error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_draw error: %s", e, exc_info=True)
