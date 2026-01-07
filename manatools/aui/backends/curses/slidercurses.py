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
- Up/Down arrows or '+'/'-' for fine-grained +/-1 changes.
- Numeric box on the right allows direct integer entry (like spinbox).
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

        # Inline numeric edit state
        self._editing = False
        self._edit_buf = ""

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
            self._logger.debug(
                "_create_backend_widget: <%s> range=[%d,%d] value=%d",
                self.debugLabel(), self._min, self._max, self._value
            )
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

            track_y = line

            # Determine width for value box on the right
            digits = max(len(str(self._min)), len(str(self._max)))
            box_w = digits + 2  # [123]
            space_w = 1
            min_track_w = 4
            have_box = width >= (min_track_w + space_w + box_w)
            track_w = width - (space_w + box_w) if have_box else width

            if track_w < min_track_w:
                return

            left = "╞"
            right = "╡"
            seg = "═"

            seg_count = max(1, track_w - 2)

            # draw endpoints and track
            try:
                window.addstr(track_y, x, left)
            except curses.error:
                pass
            try:
                window.addstr(track_y, x + 1, seg * seg_count)
            except curses.error:
                pass
            try:
                window.addstr(track_y, x + 1 + seg_count, right)
            except curses.error:
                pass

            # draw arrows first so the tick can overlay them at extremes
            try:
                if track_w >= 6:
                    window.addstr(track_y, x + 0, "◄")
                    window.addstr(track_y, x + 1 + seg_count, "►")
            except curses.error:
                pass

            # tick position clamped to interior [x+1, x+seg_count]
            rng = max(1, self._max - self._min)
            pos_frac = (self._value - self._min) / rng
            tick_x = x + 1 + int(pos_frac * max(0, seg_count - 1))
            tick_x = max(x + 1, min(x + seg_count, tick_x))
            try:
                window.addstr(track_y, tick_x, "╪")
            except curses.error:
                pass

            # Draw value box on the right if space allows
            if have_box:
                value_x = x + track_w + space_w
                if self._editing:
                    text = self._edit_buf if self._edit_buf != "" else str(self._value)
                else:
                    text = str(self._value)
                text = text[:digits].rjust(digits)
                disp = f"[{text}]"
                try:
                    if self._editing:
                        window.addstr(track_y, value_x, disp, curses.A_REVERSE)
                    else:
                        window.addstr(track_y, value_x, disp)
                except curses.error:
                    pass
        except curses.error:
            pass

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled():
            return False

        handled = True
        step = max(1, (self._max - self._min) // 20)  # ~5%

        if self._editing:
            # Editing mode: accept digits, backspace, ESC, Enter/Space
            if key in (curses.KEY_BACKSPACE, 127, 8):
                if self._edit_buf:
                    self._edit_buf = self._edit_buf[:-1]
            elif curses.ascii.isdigit(key):
                self._edit_buf += chr(key)
            elif key in (ord('-'),):
                # allow negative sign only at start and only if range allows negatives
                if self._min < 0 and (self._edit_buf == "" or self._edit_buf == "-"):
                    self._edit_buf = "" if self._edit_buf == "-" else "-"
            elif key in (ord('\n'), ord(' ')):
                self._commit_edit()
                if self.notify():
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
            elif key in (
                curses.KEY_LEFT, curses.KEY_RIGHT, curses.KEY_UP, curses.KEY_DOWN,
                curses.KEY_HOME, curses.KEY_END, curses.KEY_PPAGE, curses.KEY_NPAGE,
                ord('+'), ord('-')
            ):
                # commit and re-handle as navigation
                self._commit_edit()
                handled = False
            elif key == 9:  # Tab
                self._commit_edit()
                return False
            elif key == 27:  # ESC
                self._cancel_edit()
            else:
                handled = False

        if handled is False:
            handled = True

        if not self._editing and handled:
            if key in (curses.KEY_LEFT, ord('h')):
                self.setValue(self._value - step)
            elif key in (curses.KEY_RIGHT, ord('l')):
                self.setValue(self._value + step)
            elif key in (curses.KEY_UP, ord('+')):
                self.setValue(self._value + 1)
            elif key in (curses.KEY_DOWN, ord('-')):
                self.setValue(self._value - 1)
            elif key == curses.KEY_PPAGE:
                self.setValue(self._value - max(1, (self._max - self._min) // 5))
            elif key == curses.KEY_NPAGE:
                self.setValue(self._value + max(1, (self._max - self._min) // 5))
            elif key == curses.KEY_HOME:
                self.setValue(self._min)
            elif key == curses.KEY_END:
                self.setValue(self._max)
            elif key in (ord('\n'), ord(' ')):
                if self.notify():
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
            elif curses.ascii.isdigit(key):
                # start inline editing with first digit
                self._begin_edit(chr(key))
            else:
                handled = False

        return handled

    def _begin_edit(self, initial_char=None):
        self._editing = True
        self._edit_buf = "" if initial_char is None else str(initial_char)

    def _cancel_edit(self):
        self._editing = False
        self._edit_buf = ""

    def _commit_edit(self):
        if self._edit_buf in ("", "-"):
            self._cancel_edit()
            return
        try:
            v = int(self._edit_buf)
        except ValueError:
            self._cancel_edit()
            return
        self.setValue(v)
        self._cancel_edit()
