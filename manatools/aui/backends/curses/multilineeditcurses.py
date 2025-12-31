# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.curses contains curses backend for YMultiLineEdit

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.curses
'''
import curses
import logging
from ...yui_common import *

_mod_logger = logging.getLogger("manatools.aui.curses.multiline.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)


class YMultiLineEditCurses(YWidget):
    def __init__(self, parent=None, label=""):
        super().__init__(parent)
        self._label = label
        self._lines = [""]
        self._editing = False
        self._focused = False
        self._can_focus = True
        self._cursor_row = 0
        self._cursor_col = 0
        self._scroll_offset = 0  # topmost visible line index
        # default visible content lines (consistent across backends)
        self._default_visible_lines = 3
        # -1 means no input length limit
        self._input_max_length = -1
        # desired height (content lines + optional label row)
        self._height = self._default_visible_lines + (1 if bool(self._label) else 0)
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and _mod_logger.handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)

    def widgetClass(self):
        return "YMultiLineEdit"

    def minWidth(self):
        """Return minimal preferred width in columns when not horizontally stretchable.

        Heuristic: about 20 characters plus 1 column for a scrollbar when needed.
        Containers like `YHBoxCurses` use this to allocate space for non-stretchable
        children.
        """
        try:
            desired_chars = 20
            # reserve one column for potential scrollbar
            return int(desired_chars + 1)
        except Exception:
            return 21

    def value(self):
        try:
            return "\n".join(self._lines)
        except Exception:
            return ""

    def setValue(self, text):
        try:
            s = str(text) if text is not None else ""
        except Exception:
            s = ""
        try:
            self._lines = s.split('\n')
        except Exception:
            self._lines = [s]
        self._editing = False

    def label(self):
        return self._label

    def setLabel(self, label):
        try:
            self._label = label
            self._height = self._default_visible_lines + (1 if bool(self._label) else 0)
        except Exception:
            pass

    def setStretchable(self, dim, new_stretch):
        try:
            super().setStretchable(dim, new_stretch)
        except Exception:
            pass
        try:
            if dim == YUIDimension.YD_VERT and not self.stretchable(YUIDimension.YD_VERT):
                self._height = self._default_visible_lines + (1 if bool(self._label) else 0)
        except Exception:
            pass

    def _create_backend_widget(self):
        try:
            self._backend_widget = self
        except Exception as e:
            try:
                self._logger.exception("Error creating curses MultiLineEdit backend: %s", e)
            except Exception:
                pass

    def _set_backend_enabled(self, enabled):
        try:
            # preserve/restore focusability similar to other input widgets
            if not hasattr(self, "_saved_can_focus"):
                self._saved_can_focus = getattr(self, "_can_focus", True)
            if not enabled:
                try:
                    self._saved_can_focus = self._can_focus
                except Exception:
                    self._saved_can_focus = False
                self._can_focus = False
                self._editing = False
                self._focused = False
            else:
                try:
                    self._can_focus = bool(getattr(self, "_saved_can_focus", True))
                except Exception:
                    self._can_focus = True
        except Exception:
            pass

    def inputMaxLength(self):
        return int(getattr(self, '_input_max_length', -1))

    def setInputMaxLength(self, numberOfChars):
        try:
            self._input_max_length = int(numberOfChars)
        except Exception:
            self._input_max_length = -1

    def defaultVisibleLines(self):
        return int(getattr(self, '_default_visible_lines', 3))

    def setDefaultVisibleLines(self, newVisibleLines):
        try:
            self._default_visible_lines = int(newVisibleLines)
            self._height = self._default_visible_lines + (1 if bool(self._label) else 0)
        except Exception:
            pass

    def _desired_height_for_width(self, width: int) -> int:
        try:
            # minimal height independent from width: default visible lines + label row
            return max(1, self._default_visible_lines + (1 if bool(self._label) else 0))
        except Exception:
            return max(1, getattr(self, '_height', 1))

    def _draw(self, window, y, x, width, height):
        try:
            # Draw label (if present) and up to available lines
            line = y
            if self._label:
                try:
                    lbl_txt = str(self._label) + ':'
                    lbl_out = lbl_txt[:max(0, width)]
                    window.addstr(line, x, lbl_out)
                except Exception:
                    pass
                line += 1

            # content area excluding label
            content_h = max(1, height - (1 if self._label else 0))
            if content_h <= 0:
                return

            # Compute effective width respecting horizontal stretch
            desired_w = self.minWidth()
            eff_width = width if self.stretchable(YUIDimension.YD_HORIZ) else min(width, desired_w)

            # Reserve 1 column for scrollbar if needed
            bar_w = 1 if len(self._lines) > content_h else 0
            content_w = max(1, eff_width - bar_w)

            # Ensure scroll offset keeps cursor visible
            try:
                if self._cursor_row < self._scroll_offset:
                    self._scroll_offset = self._cursor_row
                elif self._cursor_row >= self._scroll_offset + content_h:
                    self._scroll_offset = self._cursor_row - content_h + 1
                self._scroll_offset = max(0, min(self._scroll_offset, max(0, len(self._lines) - content_h)))
            except Exception:
                pass

            # Draw visible lines
            for i in range(content_h):
                idx = self._scroll_offset + i
                out = self._lines[idx] if 0 <= idx < len(self._lines) else ""
                # clip horizontally
                clipped = out[:max(0, content_w)]
                try:
                    attr = curses.A_REVERSE if self._focused else curses.A_NORMAL
                    window.addstr(line + i, x, clipped.ljust(content_w), attr)
                except Exception:
                    pass

            # Draw cursor if focused and enabled
            try:
                if self._focused and self.isEnabled():
                    vis_row = self._cursor_row - self._scroll_offset
                    if 0 <= vis_row < content_h:
                        vis_col = min(max(0, self._cursor_col), content_w - 1)
                        try:
                            window.chgat(line + vis_row, x + vis_col, 1, curses.A_REVERSE | curses.A_BOLD)
                        except Exception:
                            pass
            except Exception:
                pass

            # Draw vertical scrollbar
            if bar_w == 1:
                try:
                    for r in range(content_h):
                        window.addch(line + r, x + content_w, '|')
                    if len(self._lines) > content_h:
                        pos = int((self._scroll_offset / max(1, len(self._lines) - content_h)) * (content_h - 1))
                        pos = max(0, min(content_h - 1, pos))
                        window.addch(line + pos, x + content_w, '#')
                except curses.error:
                    pass
        except curses.error as e:
            try:
                self._logger.error("_draw curses.error: %s", e, exc_info=True)
            except Exception:
                pass

    def _handle_key(self, key):
        """Multiline edit with cursor navigation and scrolling.

        - Arrow keys move the cursor; Home/End to line ends.
        - Enter inserts a new line; Backspace/Delete remove chars across lines.
        - Printable characters insert at cursor.
        - PageUp/PageDown scroll the view.
        - Ctrl-S posts ValueChanged (explicit commit), but we also post on each edit.
        """
        if not getattr(self, '_focused', False) or not self.isEnabled():
            return False

        try:
            total_lines = len(self._lines) if self._lines else 1
            if self._cursor_row >= total_lines:
                self._cursor_row = max(0, total_lines - 1)
            if self._cursor_col > len(self._lines[self._cursor_row]):
                self._cursor_col = len(self._lines[self._cursor_row])

            edited = False

            # Navigation
            if key == curses.KEY_UP:
                if self._cursor_row > 0:
                    self._cursor_row -= 1
                    self._cursor_col = min(self._cursor_col, len(self._lines[self._cursor_row]))
                return True
            if key == curses.KEY_DOWN:
                if self._cursor_row + 1 < len(self._lines):
                    self._cursor_row += 1
                    self._cursor_col = min(self._cursor_col, len(self._lines[self._cursor_row]))
                return True
            if key == curses.KEY_LEFT:
                if self._cursor_col > 0:
                    self._cursor_col -= 1
                elif self._cursor_row > 0:
                    self._cursor_row -= 1
                    self._cursor_col = len(self._lines[self._cursor_row])
                return True
            if key == curses.KEY_RIGHT:
                line_len = len(self._lines[self._cursor_row])
                if self._cursor_col < line_len:
                    self._cursor_col += 1
                elif self._cursor_row + 1 < len(self._lines):
                    self._cursor_row += 1
                    self._cursor_col = 0
                return True
            if key == curses.KEY_HOME:
                self._cursor_col = 0
                return True
            if key == curses.KEY_END:
                self._cursor_col = len(self._lines[self._cursor_row])
                return True
            if key == curses.KEY_PPAGE:  # PageUp
                self._scroll_offset = max(0, self._scroll_offset - max(1, self._default_visible_lines))
                return True
            if key == curses.KEY_NPAGE:  # PageDown
                max_off = max(0, len(self._lines) - max(1, self._default_visible_lines))
                self._scroll_offset = min(max_off, self._scroll_offset + max(1, self._default_visible_lines))
                return True

            # Commit (explicit)
            if key == 19:  # Ctrl-S
                dlg = self.findDialog()
                if dlg is not None and self.notify():
                    try:
                        dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
                    except Exception:
                        pass
                return True

            # Cancel editing (ESC) - keep content
            if key == 27:
                self._editing = False
                return True

            # Backspace
            if key in (curses.KEY_BACKSPACE, 127, 8):
                if self._cursor_col > 0:
                    line = self._lines[self._cursor_row]
                    self._lines[self._cursor_row] = line[:self._cursor_col - 1] + line[self._cursor_col:]
                    self._cursor_col -= 1
                    edited = True
                else:
                    if self._cursor_row > 0:
                        # merge with previous line
                        prev_len = len(self._lines[self._cursor_row - 1])
                        self._lines[self._cursor_row - 1] += self._lines[self._cursor_row]
                        self._lines.pop(self._cursor_row)
                        self._cursor_row -= 1
                        self._cursor_col = prev_len
                        edited = True
                
            # Delete
            elif key == curses.KEY_DC:
                line = self._lines[self._cursor_row]
                if self._cursor_col < len(line):
                    self._lines[self._cursor_row] = line[:self._cursor_col] + line[self._cursor_col + 1:]
                    edited = True
                else:
                    # merge with next line
                    if self._cursor_row + 1 < len(self._lines):
                        self._lines[self._cursor_row] += self._lines[self._cursor_row + 1]
                        self._lines.pop(self._cursor_row + 1)
                        edited = True

            # Enter -> new line
            elif key in (10, ord('\n')):
                line = self._lines[self._cursor_row]
                left, right = line[:self._cursor_col], line[self._cursor_col:]
                self._lines[self._cursor_row] = left
                self._lines.insert(self._cursor_row + 1, right)
                self._cursor_row += 1
                self._cursor_col = 0
                edited = True

            # Printable char
            elif 32 <= key <= 126:
                ch = chr(key)
                line = self._lines[self._cursor_row]
                # enforce per-line input max length
                if getattr(self, '_input_max_length', -1) >= 0 and len(line) >= self._input_max_length:
                    return True
                self._lines[self._cursor_row] = line[:self._cursor_col] + ch + line[self._cursor_col:]
                self._cursor_col += 1
                edited = True
            else:
                return False

            if edited:
                # post value-changed on each edit
                dlg = self.findDialog()
                if dlg is not None and self.notify():
                    try:
                        dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
                    except Exception:
                        pass
                return True

            return True
        except Exception:
            return False
