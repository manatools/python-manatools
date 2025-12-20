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
from ...yui_common import *


class YSelectionBoxCurses(YSelectionWidget):
    def __init__(self, parent=None, label=""):
        super().__init__(parent)
        self._label = label
        self._value = ""
        self._selected_items = []
        self._multi_selection = False

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

    def setValue(self, text):
        """Select first item matching text."""
        self._value = text
        # update model flags and selected_items
        self._selected_items = []
        try:
            for it in self._items:
                try:
                    if it.label() == text:
                        try:
                            it.setSelected(True)
                        except Exception:
                            pass
                        self._selected_items.append(it)
                    else:
                        if not self._multi_selection:
                            try:
                                it.setSelected(False)
                            except Exception:
                                pass
                except Exception:
                    pass
            if not self._multi_selection and len(self._selected_items) > 1:
                last = self._selected_items[-1]
                for it in list(self._selected_items)[:-1]:
                    try:
                        it.setSelected(False)
                    except Exception:
                        pass
                self._selected_items = [last]
        except Exception:
            pass
        # update hover to first matching index
        for idx, it in enumerate(self._items):
            if it.label() == text:
                self._hover_index = idx
                # adjust scroll offset to make hovered visible
                self._ensure_hover_visible()
                break

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
                # clear other model flags
                for it in self._items:
                    try:
                        if it is not self._items[idx]:
                            it.setSelected(False)
                    except Exception:
                        pass
                self._selected_items = [self._items[idx]]
                self._value = self._items[idx].label()
                try:
                    self._items[idx].setSelected(True)
                except Exception:
                    pass
            else:
                if self._items[idx] not in self._selected_items:
                    self._selected_items.append(self._items[idx])
                    try:
                        self._items[idx].setSelected(True)
                    except Exception:
                        pass
        else:
            if self._items[idx] in self._selected_items:
                self._selected_items.remove(self._items[idx])
                try:
                    self._items[idx].setSelected(False)
                except Exception:
                    pass
                self._value = self._selected_items[0].label() if self._selected_items else ""

        # ensure hover and scroll reflect this item
        self._hover_index = idx
        self._ensure_hover_visible()

    def setMultiSelection(self, enabled):
        self._multi_selection = bool(enabled)
        # if disabling multi-selection, reduce to first selected item
        if not self._multi_selection and len(self._selected_items) > 1:
            first = self._selected_items[0]
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
        if self._hover_index >= len(self._items):
             self._hover_index = max(0, len(self._items) - 1)
        self._ensure_hover_visible()
        # reset the cached visible rows so future navigation uses the next draw's value
        self._current_visible_rows = None
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
                            last = it
                    except Exception:
                        pass
                if last is not None:
                    sel = [last]
            self._selected_items = sel
            self._value = self._selected_items[0].label() if self._selected_items else ""
            if self._selected_items:
                try:
                    idx = self._items.index(self._selected_items[0])
                    self._hover_index = idx
                    self._ensure_hover_visible()
                except Exception:
                    pass
        except Exception:
            pass

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
                    display = display[:max(0, width - 3)] + "..."
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
        handled = True
        if key == curses.KEY_UP:
            if self._hover_index > 0:
                self._hover_index -= 1
                self._ensure_hover_visible()
        elif key == curses.KEY_DOWN:
            if self._hover_index < max(0, len(self._items) - 1):
                self._hover_index += 1
                self._ensure_hover_visible()
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
                    if item in self._selected_items:
                        self._selected_items.remove(item)
                        item.setSelected(False)
                    else:
                        self._selected_items.append(item)
                        item.setSelected(True)
                    # update primary value to first selected or empty
                    self._value = self._selected_items[0].label() if self._selected_items else ""
                else:
                    # single selection: set as sole selected and clear other model flags
                    it = self._selected_items[0] if self._selected_items else None
                    if it is not None:
                        it.setSelected(False)                    
                    self._selected_items = [item]
                    self._value = item.label()
                    item.setSelected(True)
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
        except Exception:
            return
        try:
            new_item.setIndex(len(self._items) - 1)
        except Exception:
            pass

        try:
            if new_item.selected():
                if not self._multi_selection:
                    try:
                        for it in self._items[:-1]:
                            try:
                                it.setSelected(False)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    self._selected_items = []

                try:
                    if new_item not in self._selected_items:
                        self._selected_items.append(new_item)
                except Exception:
                    pass

                try:
                    self._value = new_item.label()
                except Exception:
                    pass
        except Exception:
            pass
