# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.curses contains all curses backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.curses
'''
'''
NCurses backend DumbTab: simple single-selection tab bar with one content area.

- Renders a one-line tab bar with labels; the selected tab is highlighted.
- Acts as a single-child container: applications typically attach a ReplacePoint.
- Emits WidgetEvent(Activated) when the active tab changes.
'''
import curses
import curses.ascii
import logging
from ...yui_common import *

_mod_logger = logging.getLogger("manatools.aui.curses.dumbtab.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)

class YDumbTabCurses(YSelectionWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        self._backend_widget = self  # curses uses self for drawing
        self._active_index = -1
        self._focused = False
        self._can_focus = True
        self._height = 2  # tab bar + at least one row for content
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)

    def widgetClass(self):
        return "YDumbTab"

    def _create_backend_widget(self):
        # Initialize selection state based on items
        try:
            idx = -1
            for i, it in enumerate(self._items):
                if it.selected():
                    idx = i
            if idx < 0 and len(self._items) > 0:
                idx = 0
                try:
                    self._items[0].setSelected(True)
                except Exception:
                    pass
            self._active_index = idx
            self._selected_items = [ self._items[idx] ] if idx >= 0 else []
            self._logger.debug("_create_backend_widget: active=%d items=%d", self._active_index, len(self._items))
        except Exception:
            pass
        self._backend_widget = self

    def addChild(self, child):
        # single child only
        if self.hasChildren():
            raise YUIInvalidWidgetException("YDumbTab can only have one child")
        super().addChild(child)

    def addItem(self, item):
        super().addItem(item)
        # If this is the first item and nothing selected, select it
        try:
            if self._active_index < 0 and len(self._items) > 0:
                self._active_index = 0
                try:
                    self._items[0].setSelected(True)
                except Exception:
                    pass
                self._selected_items = [ self._items[0] ]
        except Exception:
            pass

    def selectItem(self, item, selected=True):
        # single selection: set as active
        if not selected:
            return
        try:
            target = None
            for i, it in enumerate(self._items):
                if it is item or it.label() == item.label():
                    target = i
                    break
            if target is None:
                return
            self._active_index = target
            for i, it in enumerate(self._items):
                try:
                    it.setSelected(i == target)
                except Exception:
                    pass
            self._selected_items = [ self._items[target] ] if target >= 0 else []
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        try:
            self._can_focus = bool(enabled)
            if not enabled and self._focused:
                self._focused = False
        except Exception:
            pass

    def _draw(self, window, y, x, width, height):
        try:
            # Draw tab bar (one line)
            bar_y = y
            col = x
            for i, it in enumerate(self._items):
                label = it.label()
                text = f" {label} "
                attr = curses.A_REVERSE if i == self._active_index and self.isEnabled() else curses.A_BOLD
                if not self.isEnabled():
                    attr |= curses.A_DIM
                # clip if needed
                if col >= x + width:
                    break
                avail = x + width - col
                to_draw = text[:max(0, avail)]
                try:
                    window.addstr(bar_y, col, to_draw, attr)
                except curses.error:
                    pass
                col += len(text) + 1
            # Draw a separator line below tabs if space
            if height > 1:
                try:
                    sep = "-" * max(0, width)
                    window.addstr(y + 1, x, sep[:width])
                except curses.error:
                    pass
            # Delegate content to single child (if any)
            ch = self.firstChild()
            if ch is not None and height > 2:
                try:
                    ch._draw(window, y + 2, x, width, height - 2)
                except Exception:
                    pass
        except curses.error:
            pass

    def _handle_key(self, key):
        if not self._can_focus or not self.isEnabled():
            return False
        handled = True
        if key in (curses.KEY_LEFT, curses.ascii.TAB):
            if self._active_index > 0:
                self._active_index -= 1
                self._update_from_active(change_reason=YEventReason.Activated)
        elif key in (curses.KEY_RIGHT,):
            if self._active_index < len(self._items) - 1:
                self._active_index += 1
                self._update_from_active(change_reason=YEventReason.Activated)
        elif key in (ord('\n'), ord(' ')):
            # activate current
            self._update_from_active(change_reason=YEventReason.Activated)
        else:
            handled = False
        return handled

    def _update_from_active(self, change_reason=YEventReason.SelectionChanged):
        try:
            for i, it in enumerate(self._items):
                try:
                    it.setSelected(i == self._active_index)
                except Exception:
                    pass
            self._selected_items = [ self._items[self._active_index] ] if 0 <= self._active_index < len(self._items) else []
            if self.notify():
                dlg = self.findDialog()
                if dlg is not None:
                    dlg._post_event(YWidgetEvent(self, change_reason))
        except Exception:
            pass
