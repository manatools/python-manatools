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
from typing import Optional
import logging
from ...yui_common import *

# Module-level safe logging setup: add a StreamHandler by default only if
# the root logger has no handlers so main can fully configure logging later.
_mod_logger = logging.getLogger("manatools.aui.curses.selectionbox.module")
if not logging.getLogger().handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(h)
    _mod_logger.setLevel(logging.INFO)


class YSelectionBoxCurses(YSelectionWidget):
    def __init__(self, parent=None, label="", multi_selection: Optional[bool] = False):
        super().__init__(parent)
        # per-instance logger named by package/backend/class
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            # ensure instance logger at least inherits module handler if root not configured
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        self._logger.debug("YSelectionBoxCurses.__init__ label=%s", label)
        self._label = label
        self._value = ""
        self._selected_items = []
        self._multi_selection = multi_selection

        # UI state for drawing/navigation
        # actual minimal height for layout (keep small so parent can expand it)
        self._height = 1
        # preferred rows used for paging when no draw happened yet
        self._preferred_rows = 6
        
        self._scroll_offset = 0
        self._hover_index = 0  # index into self._items (global)
        self._can_focus = True
        self._focused = False
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)

        # Track last computed visible rows during last _draw call so
        # navigation/ensure logic uses actual available space.
        self._current_visible_rows = None

    def widgetClass(self):
        return "YSelectionBox"

    def label(self):
        return self._label

    def value(self):
        return self._value

    def selectedItems(self):
        return list(self._selected_items)

    def selectItem(self, item, selected=True):
        """Programmatically select/deselect an item."""
        # find index
        idx = None
        for i, it in enumerate(self._items):
            if it is item or it.label() == item.label():
                idx = i
                break
        if idx is None:
            return

        if selected:
            if not self._multi_selection:
                if item not in self._selected_items:
                    selected_item = self._selected_items[0] if self._selected_items else None
                    if selected_item is not None:
                        selected_item.setSelected(False)
                    self._selected_items = [item]
                    self._value = item.label()
                    item.setSelected(True)
            else:
                if item not in self._selected_items:
                    self._selected_items.append(item)
                    item.setSelected(True)
        else:
            if item in self._selected_items:
                self._selected_items.remove(item)
                item.setSelected(False)
                self._value = self._selected_items[0].label() if self._selected_items else ""

        # ensure hover and scroll reflect this item
        self._hover_index = idx
        self._ensure_hover_visible()

    def setMultiSelection(self, enabled):
        self._multi_selection = bool(enabled)
        # if disabling multi-selection, reduce to first selected item
        if not self._multi_selection and len(self._selected_items) > 1:
            first = self._selected_items[0]
            for it in list(self._selected_items)[1:]:
                it.setSelected(False)
            self._selected_items = [first]
            self._value = first.label()

    def multiSelection(self):
        return bool(self._multi_selection)

    def _ensure_hover_visible(self):
        """Adjust scroll offset so that hover_index is visible in the box."""
        # Prefer the visible row count computed during the last _draw call
        # (which takes the actual available height into account). Fallback
        # to the configured visible row count if no draw happened yet.
        visible = self._current_visible_rows if self._current_visible_rows is not None else self._visible_row_count()
        if visible <= 0:
            return
        if self._hover_index < self._scroll_offset:
            self._scroll_offset = self._hover_index
        elif self._hover_index >= self._scroll_offset + visible:
            self._scroll_offset = self._hover_index - visible + 1

    def _visible_row_count(self):
        # Return preferred visible rows for navigation (PageUp/PageDown step).
        # Use preferred_rows (default 6) rather than forcing the layout minimum.
        return max(1, getattr(self, "_preferred_rows", 6))

    def _create_backend_widget(self):
        # No curses backend widget object; drawing handled in _draw.
        # Keep minimal layout height small so parent can give more space.
        self._height = len(self._items) + (1 if self._label else 0)
        # reset scroll/hover if out of range
        self._hover_index = 0
        # reset the cached visible rows so future navigation uses the next draw's value
        self._current_visible_rows = None
        self._ensure_hover_visible()
        # Reflect model YItem.selected flags into internal state so selection is visible
        try:
            sel = []
            if self._multi_selection:
                for it in self._items:
                    try:
                        if it.selected():
                            sel.append(it)
                    except Exception:
                        pass
            else:
                last = None
                for it in self._items:
                    try:
                        if it.selected():
                            if last is not None:
                               last.setSelected(False)
                            last = it
                    except Exception:
                        pass
                if last is not None:
                    sel = [last]
            self._selected_items = sel
            self._value = self._selected_items[0].label() if self._selected_items else ""
            _mod_logger.debug("_create_backend_widget: <%s> selected_items=<%r> value=<%r>", self.debugLabel(), self._selected_items, self._value)
        except Exception:
            pass
        self._backend_widget = self

    def _set_backend_enabled(self, enabled):
        """Enable/disable selection box: affect focusability and propagate to row items."""
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
            # propagate logical enabled state to contained items (if they are YWidget)
            try:
                for it in list(getattr(self, "_items", []) or []):
                    if hasattr(it, "setEnabled"):
                        try:
                            it.setEnabled(enabled)
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            pass

    def _draw(self, window, y, x, width, height):
        try:
            line = y
            # draw label if present
            if self._label:
                lbl = self._label
                lbl_attr = curses.A_BOLD
                if not self.isEnabled():
                    lbl_attr |= curses.A_DIM
                try:
                    window.addstr(line, x, lbl[:width], lbl_attr)
                except curses.error:
                    pass
                line += 1

            visible = self._visible_row_count()
            available_rows = max(0, height - (1 if self._label else 0))
            if self.stretchable(YUIDimension.YD_VERT):
                visible = min(len(self._items), available_rows)
            else:
                visible = min(len(self._items), self._visible_row_count(), available_rows)
            self._current_visible_rows = visible

            for i in range(visible):
                item_idx = self._scroll_offset + i
                if item_idx >= len(self._items):
                    break
                item = self._items[item_idx]
                text = item.label()
                checkbox = "*" if item in self._selected_items else " "
                display = f"[{checkbox}] {text}"
                if len(display) > width:
                    display = display[:max(0, width - 1)] + "…"
                attr = curses.A_NORMAL
                if not self.isEnabled():
                    attr |= curses.A_DIM
                if self._focused and item_idx == self._hover_index and self.isEnabled():
                    attr |= curses.A_REVERSE
                try:
                    window.addstr(line + i, x, display.ljust(width), attr)
                except curses.error:
                    pass

            if self._focused and len(self._items) > visible and width > 0 and self.isEnabled():
                try:
                    if self._scroll_offset > 0:
                        window.addch(y + (1 if self._label else 0), x + width - 1, '^')
                    if (self._scroll_offset + visible) < len(self._items):
                        window.addch(y + (1 if self._label else 0) + visible - 1, x + width - 1, 'v')
                except curses.error:
                    pass
        except curses.error:
            pass

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled():
            return False
        self._logger.debug("_handle_key called key=%r focused=%s hover_index=%d", key, self._focused, self._hover_index)
        handled = True
        if key == curses.KEY_UP:
            if self._hover_index > 0:
                self._hover_index -= 1
                self._ensure_hover_visible()
                self._logger.debug("hover moved up -> %d", self._hover_index)
        elif key == curses.KEY_DOWN:
            if self._hover_index < max(0, len(self._items) - 1):
                self._hover_index += 1
                self._ensure_hover_visible()
                self._logger.debug("hover moved down -> %d", self._hover_index)
        elif key == curses.KEY_PPAGE:  # PageUp
            step = self._visible_row_count() or 1
            self._hover_index = max(0, self._hover_index - step)
            self._ensure_hover_visible()
        elif key == curses.KEY_NPAGE:  # PageDown
            step = self._visible_row_count() or 1
            self._hover_index = min(max(0, len(self._items) - 1), self._hover_index + step)
            self._ensure_hover_visible()
        elif key == curses.KEY_HOME:
            self._hover_index = 0
            self._ensure_hover_visible()
        elif key == curses.KEY_END:
            self._hover_index = max(0, len(self._items) - 1)
            self._ensure_hover_visible()
        elif key in (ord(' '), ord('\n')):  # toggle/select
            if 0 <= self._hover_index < len(self._items):
                item = self._items[self._hover_index]
                if self._multi_selection:
                    # toggle membership and update model flag
                    was_selected = item in self._selected_items
                    if was_selected:
                        self._selected_items.remove(item)
                        try:
                            item.setSelected(False)
                        except Exception:
                            pass
                        self._logger.info("item deselected: <%s>", item.label())
                    else:
                        self._selected_items.append(item)
                        try:
                            item.setSelected(True)
                        except Exception:
                            pass
                        self._logger.info("item selected: <%s>", item.label())
                    # update primary value to first selected or empty
                    self._value = self._selected_items[0].label() if self._selected_items else ""
                else:
                    # single selection: set as sole selected and clear other model flags
                    it = self._selected_items[0] if self._selected_items else None
                    if it is not None:
                        try:
                            it.setSelected(False)
                        except Exception:
                            pass
                    self._selected_items = [item]
                    self._value = item.label()
                    try:
                        item.setSelected(True)
                    except Exception:
                        pass
                    self._logger.info("single selection set: %s", item.label())
                # notify dialog of selection change
                if self.notify():
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
        else:
            handled = False

        return handled


    def addItem(self, item):
        """Add item to model; if item has selected flag, update internal selection state.
           Do not emit notification on add.
        """
        super().addItem(item)
        try:
            new_item = self._items[-1]
            new_item.setIndex(len(self._items) - 1)
            selected_flag = False
            try:
                selected_flag = bool(new_item.selected())
            except Exception:
                selected_flag = False
            if selected_flag:
                if not self._multi_selection:
                    selected = self._selected_items[0] if self._selected_items else None
                    if selected is not None:
                        try:
                            selected.setSelected(False)
                        except Exception:
                            pass
                    self._selected_items = [new_item]
                    self._value = new_item.label()
                else:
                    self._selected_items.append(new_item)
                    self._value = self._selected_items[0].label() if self._selected_items else ""
            self._logger.debug("addItem: label=<%s> selected=<%s> value=<%r>", new_item.label(), selected_flag, self._value)
        except Exception:
            pass
