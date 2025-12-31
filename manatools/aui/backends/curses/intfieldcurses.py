import curses
import logging
from ...yui_common import *

_mod_logger = logging.getLogger("manatools.aui.curses.intfield.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)


class YIntFieldCurses(YWidget):
    def __init__(self, parent=None, label="", minValue=0, maxValue=100, initialValue=0):
        super().__init__(parent)
        self._label = label
        self._min = int(minValue)
        self._max = int(maxValue)
        self._value = int(initialValue)
        # height: 2 lines if label present (label above control), else 1
        self._height = 2 if bool(self._label) else 1
        self._focused = False
        self._can_focus = True
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and _mod_logger.handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)

    def widgetClass(self):
        return "YIntField"

    def value(self):
        return int(self._value)

    def setValue(self, val):
        try:
            v = int(val)
        except Exception:
            return
        if v < self._min:
            v = self._min
        if v > self._max:
            v = self._max
        self._value = v

    def label(self):
        return self._label

    def setLabel(self, label):
        self._label = label
        try:
            self._height = 2 if bool(self._label) else 1
        except Exception:
            pass

    def _create_backend_widget(self):
        try:
            self._backend_widget = self
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception as e:
            try:
                self._logger.exception("Error creating curses IntField backend: %s", e)
            except Exception:
                pass

    def _set_backend_enabled(self, enabled):
        try:
            # curses backend: affect focusability if needed
            if not enabled:
                self._can_focus = False
        except Exception:
            pass

    def _draw(self, window, y, x, width, height):
        try:
            # Draw label on the first line, control on the second line (if available)
            line_label = y
            line_ctrl = y if height <= 1 else y + 1

            # Draw label (if present) on its line
            if self._label:
                try:
                    lbl_txt = str(self._label) + ':'
                    # truncate if necessary
                    lbl_out = lbl_txt[:max(0, width)]
                    window.addstr(line_label, x, lbl_out)
                except Exception:
                    pass

            # Remaining width for the control
            ctrl_x = x
            ctrl_width = max(1, width)

            # Format control as: ↓ <number> ↑
            try:
                up_ch = '↑'
                down_ch = '↓'
            except Exception:
                up_ch = '^'
                down_ch = 'v'

            num_s = str(self._value)
            inner_width = max(1, ctrl_width - 4)
            if len(num_s) > inner_width:
                num_s = num_s[-inner_width:]

            pad_left = max(0, (inner_width - len(num_s)) // 2)
            pad_right = inner_width - len(num_s) - pad_left
            display = f"{down_ch} " + (' ' * pad_left) + num_s + (' ' * pad_right) + f" {up_ch}"

            if not self.isEnabled():
                attr = curses.A_DIM
            else:
                attr = curses.A_REVERSE if getattr(self, '_focused', False) else curses.A_NORMAL

            try:
                window.addstr(line_ctrl, ctrl_x, display[:ctrl_width], attr)
            except Exception:
                try:
                    window.addstr(line_ctrl, ctrl_x, num_s[:ctrl_width], attr)
                except Exception:
                    pass
        except curses.error as e:
            try:
                self._logger.error("_draw curses.error: %s", e, exc_info=True)
            except Exception:
                pass

    def _handle_key(self, key):
        """Handle keys for focusable spin-like behaviour: up/down to change value."""
        if not getattr(self, '_focused', False) or not self.isEnabled():
            return False

        changed = False
        try:
            if key == curses.KEY_UP:
                if self._value < self._max:
                    self._value += 1
                    changed = True
            elif key == curses.KEY_DOWN:
                if self._value > self._min:
                    self._value -= 1
                    changed = True
            else:
                return False
        except Exception:
            return False

        if changed:
            # Force dialog redraw next loop
            dlg = self.findDialog()
            if dlg is not None:
                try:
                    dlg._last_draw_time = 0
                except Exception:
                    pass
                # Emit value changed event if notify enabled
                try:
                    if self.notify():
                        dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
                except Exception:
                    try:
                        self._logger.debug("Failed to post ValueChanged event")
                    except Exception:
                        pass
        return True
