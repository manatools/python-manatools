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
import logging
from ...yui_common import *


class YTimeFieldCurses(YWidget):
    """NCurses backend YTimeField with three integer segments (H, M, S).
    value()/setValue() use HH:MM:SS. No change events posted.
    Navigation: Left/Right to change segment, Up/Down or +/- to change value, digits to type.
    """
    def __init__(self, parent=None, label: str = ""):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        self._label = label or ""
        self._h, self._m, self._s = 0, 0, 0
        self._seg_index = 0  # 0..2
        self._editing = False
        self._edit_buf = ""
        self._can_focus = True
        self._focused = False
        # Default: do not stretch horizontally or vertically; respects external overrides
        try:
            self.setStretchable(YUIDimension.YD_HORIZ, False)
            self.setStretchable(YUIDimension.YD_VERT, False)
        except Exception:
            pass

    def widgetClass(self):
        return "YTimeField"

    def value(self) -> str:
        return f"{self._h:02d}:{self._m:02d}:{self._s:02d}"

    def setValue(self, timestr: str):
        try:
            h, m, s = [int(p) for p in str(timestr).split(':')]
        except Exception:
            return
        self._h = max(0, min(23, h))
        self._m = max(0, min(59, m))
        self._s = max(0, min(59, s))

    def _create_backend_widget(self):
        self._backend_widget = self
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        pass

    def _draw(self, window, y, x, width, height):
        try:
            line = y
            label_to_show = self._label if self._label else (self.debugLabel() if hasattr(self, 'debugLabel') else "unknown")
            try:
                window.addstr(line, x, label_to_show[:width])
            except curses.error:
                pass
            line += 1

            parts = {'H': f"{self._h:02d}", 'M': f"{self._m:02d}", 'S': f"{self._s:02d}"}
            disp = []
            order = ['H', 'M', 'S']
            for idx, p in enumerate(order):
                seg_text = parts[p]
                if self._focused and idx == self._seg_index:
                    if self._editing:
                        buf = self._edit_buf or ''
                        seg_w = 2
                        buf_disp = buf.rjust(seg_w)
                        text = f"[{buf_disp}]"
                    else:
                        text = f"[{seg_text}]"
                else:
                    text = f" {seg_text} "
                disp.append(text)
                if idx < 2:
                    disp.append(":")
            out = ''.join(disp)
            try:
                window.addstr(line, x, out[:max(0, width)])
            except curses.error:
                pass
        except curses.error:
            pass

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled():
            return False

        if self._editing:
            if key in (curses.KEY_BACKSPACE, 127, 8):
                if self._edit_buf:
                    self._edit_buf = self._edit_buf[:-1]
                return True
            if curses.ascii.isdigit(key):
                self._edit_buf += chr(key)
                return True
            if key in (ord('\n'), ord(' ')):
                self._commit_edit()
                return True
            if key == 27:  # ESC
                self._cancel_edit()
                return True
            if key in (curses.KEY_LEFT, curses.KEY_RIGHT, curses.KEY_UP, curses.KEY_DOWN, ord('+'), ord('-')):
                self._commit_edit()
        # Non-editing navigation
        if key in (curses.KEY_LEFT,):
            self._seg_index = (self._seg_index - 1) % 3
            return True
        if key in (curses.KEY_RIGHT,):
            self._seg_index = (self._seg_index + 1) % 3
            return True
        if key in (curses.KEY_UP, ord('+')):
            self._bump(+1)
            return True
        if key in (curses.KEY_DOWN, ord('-')):
            self._bump(-1)
            return True
        if curses.ascii.isdigit(key):
            self._begin_edit(chr(key))
            return True
        return False

    def _seg_ref(self, idx):
        seg = ['H', 'M', 'S'][idx]
        if seg == 'H':
            return '_h', 0, 23
        if seg == 'M':
            return '_m', 0, 59
        return '_s', 0, 59

    def _bump(self, delta):
        name, lo, hi = self._seg_ref(self._seg_index)
        val = getattr(self, name)
        val += delta
        if val < lo: val = lo
        if val > hi: val = hi
        setattr(self, name, val)

    def _begin_edit(self, initial_char=None):
        self._editing = True
        self._edit_buf = '' if initial_char is None else str(initial_char)

    def _cancel_edit(self):
        self._editing = False
        self._edit_buf = ''

    def _commit_edit(self):
        if self._edit_buf in ('', ':'):
            self._cancel_edit()
            return
        try:
            v = int(self._edit_buf)
        except ValueError:
            self._cancel_edit()
            return
        name, lo, hi = self._seg_ref(self._seg_index)
        v = max(lo, min(hi, v))
        setattr(self, name, v)
        self._cancel_edit()
