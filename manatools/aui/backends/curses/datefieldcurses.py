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
import locale
from ...yui_common import *


def _locale_date_order():
    try:
        locale.setlocale(locale.LC_TIME, '')
    except Exception:
        pass
    try:
        fmt = locale.nl_langinfo(locale.D_FMT)
    except Exception:
        fmt = '%Y-%m-%d'
    fmt = fmt or '%Y-%m-%d'
    order = []
    i = 0
    while i < len(fmt):
        if fmt[i] == '%':
            i += 1
            if i < len(fmt):
                c = fmt[i]
                if c in ('Y', 'y'):
                    order.append('Y')
                elif c in ('m', 'b', 'B'):
                    order.append('M')
                elif c in ('d', 'e'):
                    order.append('D')
        i += 1
    for x in ['Y', 'M', 'D']:
        if x not in order:
            order.append(x)
    return order[:3]


class YDateFieldCurses(YWidget):
    """NCurses backend YDateField with three integer segments (Y, M, D) ordered per locale.
    value()/setValue() use ISO format YYYY-MM-DD. No change events posted.
    Navigation: Left/Right to change segment, Up/Down or +/- to change value, digits to type.
    """
    def __init__(self, parent=None, label: str = ""):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        self._label = label or ""
        self._y, self._m, self._d = 2000, 1, 1
        self._order = _locale_date_order()
        self._seg_index = 0  # 0..2
        self._editing = False
        self._edit_buf = ""
        self._can_focus = True
        self._focused = False

    def widgetClass(self):
        return "YDateField"

    def value(self) -> str:
        return f"{self._y:04d}-{self._m:02d}-{self._d:02d}"

    def setValue(self, datestr: str):
        try:
            y, m, d = [int(p) for p in str(datestr).split('-')]
        except Exception:
            return
        y = max(1, min(9999, y))
        m = max(1, min(12, m))
        dmax = self._days_in_month(y, m)
        d = max(1, min(dmax, d))
        self._y, self._m, self._d = y, m, d

    def _days_in_month(self, y, m):
        if m in (1,3,5,7,8,10,12):
            return 31
        if m in (4,6,9,11):
            return 30
        leap = (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0))
        return 29 if leap else 28

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

            # build ordered parts
            parts = {'Y': f"{self._y:04d}", 'M': f"{self._m:02d}", 'D': f"{self._d:02d}"}
            disp = []
            for idx, p in enumerate(self._order):
                seg_text = parts[p]
                # when focused on segment, show edit buffer if editing
                if self._focused and idx == self._seg_index:
                    if self._editing:
                        buf = self._edit_buf or ''
                        seg_w = 4 if p == 'Y' else 2
                        # right-align buffer into field width
                        buf_disp = buf.rjust(seg_w)
                        text = f"[{buf_disp}]"
                    else:
                        text = f"[{seg_text}]"
                else:
                    text = f" {seg_text} "
                disp.append(text)
                if idx < 2:
                    disp.append("-")
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

        # Editing
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
            # navigation commits and re-handles
            if key in (curses.KEY_LEFT, curses.KEY_RIGHT, curses.KEY_UP, curses.KEY_DOWN, ord('+'), ord('-')):
                self._commit_edit()
                # fall through

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
        seg = self._order[idx]
        if seg == 'Y':
            return '_y', 1, 9999
        if seg == 'M':
            return '_m', 1, 12
        # D
        return '_d', 1, self._days_in_month(self._y, self._m)

    def _bump(self, delta):
        name, lo, hi = self._seg_ref(self._seg_index)
        val = getattr(self, name)
        if name == '_d':
            hi = self._days_in_month(self._y, self._m)
        val += delta
        if val < lo: val = lo
        if val > hi: val = hi
        setattr(self, name, val)
        # adjust day when year/month change affects max days
        if name in ('_y','_m'):
            dmax = self._days_in_month(self._y, self._m)
            if self._d > dmax:
                self._d = dmax

    def _begin_edit(self, initial_char=None):
        self._editing = True
        self._edit_buf = '' if initial_char is None else str(initial_char)

    def _cancel_edit(self):
        self._editing = False
        self._edit_buf = ''

    def _commit_edit(self):
        if self._edit_buf in ('', '-'):
            self._cancel_edit()
            return
        try:
            v = int(self._edit_buf)
        except ValueError:
            self._cancel_edit()
            return
        name, lo, hi = self._seg_ref(self._seg_index)
        if name == '_d':
            hi = self._days_in_month(self._y, self._m)
        v = max(lo, min(hi, v))
        setattr(self, name, v)
        # adjust day if needed
        if name in ('_y','_m'):
            dmax = self._days_in_month(self._y, self._m)
            if self._d > dmax:
                self._d = dmax
        self._cancel_edit()
