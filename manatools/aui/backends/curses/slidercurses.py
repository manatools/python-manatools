# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.curses contains all curses backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.curses
'''
"""
NCurses backend Slider widget.
- Draws a horizontal track with Unicode box-drawing characters.
  Track: ╞═══…══╡ ; position tick: ╪ at current value.
- Left/Right arrows to change, Home/End jump to min/max, PgUp/PgDn step.
- Default stretchable horizontally.
"""
import curses
import curses.ascii
import logging
from ...yui_common import *

_mod_logger = logging.getLogger("manatools.aui.curses.slider.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)

class YSliderCurses(YWidget):
    def __init__(self, parent=None, label: str = "", minVal: int = 0, maxVal: int = 100, initialVal: int = 0):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        self._label_text = str(label) if label else ""
        self._min = int(minVal)
        self._max = int(maxVal)
        if self._min > self._max:
            self._min, self._max = self._max, self._min
        self._value = max(self._min, min(self._max, int(initialVal)))
        self._height = 2
        self._can_focus = True
        self._focused = False
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, False)

    def widgetClass(self):
        return "YSlider"

    def value(self) -> int:
        return int(self._value)

    def setValue(self, v: int):
        prev = self._value
        self._value = max(self._min, min(self._max, int(v)))
        if self._value != prev and self.notify():
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))

    def _create_backend_widget(self):
        self._backend_widget = self
        try:
            self._logger.debug("_create_backend_widget: <%s> range=[%d,%d] value=%d", self.debugLabel(), self._min, self._max, self._value)
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        pass

    def _draw(self, window, y, x, width, height):
        try:
            line = y
            # label on top if present
            if self._label_text:
                try:
                    window.addstr(line, x, self._label_text[:width])
                except curses.error:
                    pass
                line += 1
            # draw track on the next line
            track_y = line
            # Ensure minimal width for endpoints and at least one segment
            if width < 4:
                return
            # endpoints
            left = "╞"
            right = "╡"
            seg = "═"
            # compute inner width excluding endpoints and maybe arrows
            inner_w = max(1, width - 2)
            # draw left endpoint
            try:
                window.addstr(track_y, x, left)
            except curses.error:
                pass
            # draw track segments
            try:
                window.addstr(track_y, x + 1, seg * (inner_w - 1))
            except curses.error:
                pass
            # draw right endpoint
            try:
                window.addstr(track_y, x + inner_w, right)
            except curses.error:
                pass
            # position tick
            rng = max(1, self._max - self._min)
            pos_frac = (self._value - self._min) / rng
            tick_x = x + 1 + int(pos_frac * (inner_w - 1))
            try:
                window.addstr(track_y, tick_x, "╪")
            except curses.error:
                pass
            # arrows near ends for hint
            try:
                if width >= 6:
                    window.addstr(track_y, x + 0, "◄")
                    window.addstr(track_y, x + inner_w, "►")
            except curses.error:
                pass
        except curses.error:
            pass

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled():
            return False
        handled = True
        step = max(1, (self._max - self._min) // 20)  # 5% default step
        if key in (curses.KEY_LEFT, ord('h')):
            self.setValue(self._value - step)
        elif key in (curses.KEY_RIGHT, ord('l')):
            self.setValue(self._value + step)
        elif key == curses.KEY_PPAGE:
            self.setValue(self._value - max(1, (self._max - self._min) // 5))
        elif key == curses.KEY_NPAGE:
            self.setValue(self._value + max(1, (self._max - self._min) // 5))
        elif key == curses.KEY_HOME:
            self.setValue(self._min)
        elif key == curses.KEY_END:
            self.setValue(self._max)
        elif key in (ord('\n'), ord(' ')):
            # Activated event
            if self.notify():
                dlg = self.findDialog()
                if dlg is not None:
                    dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
        else:
            handled = False
        return handled
