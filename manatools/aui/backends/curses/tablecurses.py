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
import gettext
_ = gettext.gettext

# Module-level logger for table curses backend
_mod_logger = logging.getLogger("manatools.aui.curses.table.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)


class YTableCurses(YSelectionWidget):
    """
    NCurses implementation of a table widget.
    - Renders column headers and rows in a fixed-width grid.
    - Honors `YTableHeader` titles and alignments.
    - Displays checkbox columns declared via `YTableHeader.isCheckboxColumn()` as [x]/[ ].
    - Selection driven by `YTableItem.selected()`; emits SelectionChanged on change.
    - SPACE toggles the first checkbox column for the current row and emits ValueChanged.
    - ENTER toggles row selection (multi or single as configured).
    """
    def __init__(self, parent=None, header: YTableHeader = None, multiSelection: bool = False):
        super().__init__(parent)
        if header is None:
            raise ValueError("YTableCurses requires a YTableHeader")
        self._header = header
        self._multi = bool(multiSelection)
        # force single-selection if any checkbox column present
        try:
            for c_idx in range(self._header.columns()):
                if self._header.isCheckboxColumn(c_idx):
                    self._multi = False
                    break
        except Exception:
            pass
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        # UI state
        self._height = 3  # header + at least 2 rows
        self._can_focus = True
        self._focused = False
        self._hover_row = 0
        self._scroll_offset = 0
        self._selected_items = []
        # Parallel set for O(1) membership tests in _draw() (avoids O(N) list scan
        # per visible row when checking the multi-selection marker).
        self._selected_set: set = set()
        self._changed_item = None
        self._current_visible_rows = None
        # Column-width cache: maps total_width -> (widths, sep) to avoid
        # per-frame arithmetic recomputation on every _draw() call.
        self._col_width_cache = None  # (cached_total_width, widths, sep) | None
        # Per-column metadata: list of (is_checkbox, alignment) tuples computed
        # once from the header so that _draw() avoids repeated method calls inside
        # the inner visible-row × column loop.
        self._col_meta: list = []
        # widget position
        self._x = 0
        self._y = 0
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)

    def widgetClass(self):
        return "YTable"

    def _first_checkbox_col(self):
        try:
            for c in range(self._header.columns()):
                if self._header.isCheckboxColumn(c):
                    return c
        except Exception:
            pass
        return None

    def _build_col_meta(self) -> list:
        """
        Precompute (is_checkbox, alignment) tuples for every column.

        Called once when the backend is created. The result is stored in
        self._col_meta and consumed by _draw() to avoid repeated
        self._header.isCheckboxColumn() / alignment() calls inside the
        per-visible-row × per-column inner loop.
        """
        meta = []
        try:
            for c in range(self._header.columns()):
                try:
                    is_cb = bool(self._header.isCheckboxColumn(c))
                except Exception:
                    is_cb = False
                try:
                    align = self._header.alignment(c)
                except Exception:
                    align = YAlignmentType.YAlignBegin
                meta.append((is_cb, align))
        except Exception as exc:
            self._logger.debug("_build_col_meta: %s", exc)
        return meta

    def _create_backend_widget(self):
        # Associate backend with self, compute minimal height, and reflect model selection.
        self._backend_widget = self
        self._height = max(3, 1 + min(len(self._items), 6))
        # ensure visibility affects focusability on creation
        try:
            self._can_focus = bool(self._visible)
        except Exception:
            pass
        # Build internal selection list from item flags
        sel = []
        try:
            if self._multi:
                for it in list(getattr(self, '_items', []) or []):
                    try:
                        if it.selected():
                            sel.append(it)
                    except Exception:
                        pass
            else:
                chosen = None
                for it in list(getattr(self, '_items', []) or []):
                    try:
                        if it.selected():
                            chosen = it
                    except Exception:
                        pass
                if chosen is not None:
                    sel = [chosen]
        except Exception:
            pass
        self._selected_items = sel
        self._selected_set = set(sel)
        self._hover_row = 0
        self._scroll_offset = 0
        self._current_visible_rows = None
        # Pre-build column metadata so _draw() does not call header methods per row.
        self._col_meta = self._build_col_meta()
        self._col_width_cache = None
        self._logger.debug(
            "_create_backend_widget: items=%d selected=%d col_meta=%d",
            len(self._items) if self._items else 0,
            len(self._selected_items),
            len(self._col_meta),
        )
        # respect initial enabled state
        try:
            self._set_backend_enabled(self.isEnabled())
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        try:
            self._can_focus = bool(enabled)
            if not enabled:
                self._focused = False
            # propagate logical enabled state to contained items
            for it in list(getattr(self, '_items', []) or []):
                if hasattr(it, 'setEnabled'):
                    try:
                        it.setEnabled(enabled)
                    except Exception:
                        pass
        except Exception:
            pass

    def _visible_row_count(self):
        # number of rows available excluding the header line
        return max(1, getattr(self, "_preferred_rows", 6))

    def _ensure_hover_visible(self):
        visible = self._current_visible_rows if self._current_visible_rows is not None else self._visible_row_count()
        if visible <= 0:
            return
        if self._hover_row < self._scroll_offset:
            self._scroll_offset = self._hover_row
        elif self._hover_row >= self._scroll_offset + visible:
            self._scroll_offset = self._hover_row - visible + 1

    def _col_widths(self, total_width):
        """
        Return (widths, sep) for *total_width* characters.

        The result is cached by total_width to avoid repeating the arithmetic
        on every _draw() call. The cache is invalidated automatically when the
        terminal is resized and total_width changes.
        """
        cache = getattr(self, '_col_width_cache', None)
        if cache is not None and cache[0] == total_width:
            return cache[1], cache[2]
        try:
            cols = max(1, int(self._header.columns()))
        except Exception:
            cols = 1
        # Divide width equally across columns with a 1-character separator.
        sep = 1
        usable = max(1, total_width - (cols - 1) * sep)
        base = max(1, usable // cols)
        widths = [base] * cols
        remainder = usable - base * cols
        for i in range(remainder):
            widths[i] += 1
        self._col_width_cache = (total_width, widths, sep)
        return widths, sep

    def _align_text(self, text, width, align: YAlignmentType):
        s = str(text)[:width]
        if align == YAlignmentType.YAlignCenter:
            pad = max(0, width - len(s))
            left = pad // 2
            right = pad - left
            return (" " * left) + s + (" " * right)
        elif align == YAlignmentType.YAlignEnd:
            return s.rjust(width)
        else:
            return s.ljust(width)

    def _draw(self, window, y, x, width, height):
        if self._visible is False:
            return
        try:
            line = y
            # Header
            widths, sep = self._col_widths(width)
            headers = []
            try:
                for c in range(self._header.columns()):
                    lbl = self._header.header(c)
                    align = self._header.alignment(c)
                    headers.append(self._align_text(lbl, widths[c], align))
            except Exception:
                # fallback single empty header
                headers = [" ".ljust(widths[0])]
            header_line = (" " * sep).join(headers)
            # If multi-selection without checkbox columns, reserve left space for selection marker
            use_selection_marker = False
            try:
                use_selection_marker = self._multi and (self._first_checkbox_col() is None)
            except Exception:
                use_selection_marker = False
            if use_selection_marker:
                header_line = "    " + header_line
            self._x = x
            self._y = line
            try:
                window.addstr(line, x, header_line[:width], curses.A_BOLD)
            except curses.error:
                pass
            line += 1

            # Rows
            available_rows = max(0, height - 1)
            visible = min(len(self._items), available_rows)
            if self.stretchable(YUIDimension.YD_VERT):
                visible = min(len(self._items), available_rows)
            else:
                visible = min(len(self._items), self._visible_row_count(), available_rows)
            self._current_visible_rows = visible

            for i in range(visible):
                row_idx = self._scroll_offset + i
                if row_idx >= len(self._items):
                    break
                it = self._items[row_idx]
                cells = []
                # Use precomputed column metadata to avoid header method calls
                # inside the inner visible-row × column loop.
                col_meta = self._col_meta if self._col_meta else self._build_col_meta()
                for c in range(len(widths)):
                    try:
                        cell = it.cell(c)
                    except Exception:
                        cell = None
                    if c < len(col_meta):
                        is_cb, align = col_meta[c]
                    else:
                        is_cb = False
                        align = YAlignmentType.YAlignBegin
                    if is_cb:
                        val = False
                        try:
                            val = cell.checked() if cell is not None else False
                        except Exception:
                            val = False
                        txt = "[x]" if val else "[ ]"
                    else:
                        txt = ""
                        try:
                            txt = cell.label() if cell is not None else ""
                        except Exception:
                            txt = ""
                    cells.append(self._align_text(txt, widths[c], align))
                row_text = (" " * sep).join(cells)
                # selection marker for multi-selection without checkbox columns
                if use_selection_marker:
                    try:
                        # _selected_set gives O(1) membership test vs O(N) list scan.
                        marker = "[x] " if (it in self._selected_set) else "[ ] "
                    except Exception:
                        marker = "[ ] "
                    row_text = marker + row_text
                attr = curses.A_NORMAL
                if not self.isEnabled():
                    attr |= curses.A_DIM
                if self._focused and row_idx == self._hover_row and self.isEnabled():
                    attr |= curses.A_REVERSE
                try:
                    window.addstr(line + i, x, row_text[:width].ljust(width), attr)
                except curses.error:
                    pass

            # simple scroll indicators
            if self._focused and len(self._items) > visible and width > 0 and self.isEnabled():
                try:
                    if self._scroll_offset > 0:
                        window.addch(y + 1, x + width - 1, '↑', curses.A_REVERSE)
                    if (self._scroll_offset + visible) < len(self._items):
                        window.addch(y + visible, x + width - 1, '↓', curses.A_REVERSE)
                except curses.error:
                    pass
        except curses.error:
            pass

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled() or not self.visible():
            return False
        handled = True
        if key == curses.KEY_UP:
            if self._hover_row > 0:
                self._hover_row -= 1
                self._ensure_hover_visible()
        elif key == curses.KEY_DOWN:
            if self._hover_row < max(0, len(self._items) - 1):
                self._hover_row += 1
                self._ensure_hover_visible()
        elif key == curses.KEY_PPAGE:
            step = self._visible_row_count() or 1
            self._hover_row = max(0, self._hover_row - step)
            self._ensure_hover_visible()
        elif key == curses.KEY_NPAGE:
            step = self._visible_row_count() or 1
            self._hover_row = min(max(0, len(self._items) - 1), self._hover_row + step)
            self._ensure_hover_visible()
        elif key == curses.KEY_HOME:
            self._hover_row = 0
            self._ensure_hover_visible()
        elif key == curses.KEY_END:
            self._hover_row = max(0, len(self._items) - 1)
            self._ensure_hover_visible()
        elif key in (ord(' '),):  # toggle checkbox or selection if no checkbox columns
            col = self._first_checkbox_col()
            if 0 <= self._hover_row < len(self._items):
                it = self._items[self._hover_row]
                if col is not None:
                    # Toggle checkbox value
                    cell = None
                    try:
                        cell = it.cell(col)
                    except Exception:
                        cell = None
                    if cell is not None:
                        try:
                            cell.setChecked(not bool(cell.checked()))
                            self._changed_item = it
                        except Exception:
                            pass
                        # notify value changed
                        if self.notify():
                            dlg = self.findDialog()
                            if dlg is not None:
                                dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
                else:
                    # Use SPACE to toggle row selection in multi-selection mode
                    if self._multi:
                        was_selected = it in self._selected_set
                        if was_selected:
                            try:
                                it.setSelected(False)
                            except Exception:
                                pass
                            try:
                                self._selected_items.remove(it)
                                self._selected_set.discard(it)
                            except Exception:
                                pass
                        else:
                            try:
                                it.setSelected(True)
                            except Exception:
                                pass
                            self._selected_items.append(it)
                            self._selected_set.add(it)
                        # notify selection change
                        if self.notify():
                            dlg = self.findDialog()
                            if dlg is not None:
                                dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
        elif key in (ord('\n'),):  # toggle row selection
            if 0 <= self._hover_row < len(self._items):
                it = self._items[self._hover_row]
                if self._multi:
                    was_selected = it in self._selected_set
                    if was_selected:
                        try:
                            it.setSelected(False)
                        except Exception:
                            pass
                        try:
                            self._selected_items.remove(it)
                            self._selected_set.discard(it)
                        except Exception:
                            pass
                    else:
                        try:
                            it.setSelected(True)
                        except Exception:
                            pass
                        self._selected_items.append(it)
                        self._selected_set.add(it)
                else:
                    # single selection: make it sole selected
                    prev = self._selected_items[0] if self._selected_items else None
                    if prev is not None:
                        try:
                            prev.setSelected(False)
                        except Exception:
                            pass
                    try:
                        it.setSelected(True)
                    except Exception:
                        pass
                    self._selected_items = [it]
                    self._selected_set = {it}
                # notify selection change
                if self.notify():
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
        else:
            handled = False
        return handled

    def key_hints(self) -> str:
        return _("↑↓=Move") + " | " + _("SPACE=Toggle") + " | " + _("ENTER=Select")

    # API
    def addItem(self, item):
        if isinstance(item, str):
            item = YTableItem(item)
        if not isinstance(item, YTableItem):
            raise TypeError("YTableCurses.addItem expects a YTableItem or string label")
        super().addItem(item)
        try:
            item.setIndex(len(self._items) - 1)
        except Exception:
            pass
        # reflect initial selected flag into internal list
        try:
            if item.selected():
                if not self._multi:
                    prev = self._selected_items[0] if self._selected_items else None
                    if prev is not None:
                        try:
                            prev.setSelected(False)
                        except Exception:
                            pass
                    self._selected_items = [item]
                    self._selected_set = {item}
                else:
                    if item not in self._selected_set:
                        self._selected_items.append(item)
                        self._selected_set.add(item)
        except Exception:
            pass

    def addItems(self, items):
        """
        Add multiple items in a single call.

        More efficient than N addItem() calls because the selection-flag scan
        is done once at the end in a single pass instead of per item.
        """
        for item in items:
            if isinstance(item, str):
                item = YTableItem(item)
            if not isinstance(item, YTableItem):
                raise TypeError("YTableCurses.addItem expects a YTableItem or string label")
            super().addItem(item)
            try:
                item.setIndex(len(self._items) - 1)
            except Exception:
                pass
        # Single-pass selection sync from model flags.
        try:
            if self._multi:
                for it in list(getattr(self, '_items', []) or []):
                    try:
                        if it.selected() and it not in self._selected_set:
                            self._selected_items.append(it)
                            self._selected_set.add(it)
                    except Exception:
                        pass
            else:
                # Last item marked selected wins in single-selection mode.
                chosen = None
                for it in reversed(list(getattr(self, '_items', []) or [])):
                    try:
                        if it.selected():
                            chosen = it
                            break
                    except Exception:
                        pass
                if chosen is not None and chosen not in self._selected_set:
                    for prev in self._selected_items:
                        try:
                            prev.setSelected(False)
                        except Exception:
                            pass
                    self._selected_items = [chosen]
                    self._selected_set = {chosen}
        except Exception as exc:
            self._logger.debug("addItems: selection sync failed: %s", exc)

    def selectItem(self, item, selected=True):
        try:
            item.setSelected(bool(selected))
        except Exception:
            pass
        if selected:
            if not self._multi:
                prev = self._selected_items[0] if self._selected_items else None
                if prev is not None:
                    try:
                        prev.setSelected(False)
                    except Exception:
                        pass
                self._selected_items = [item]
                self._selected_set = {item}
            else:
                if item not in self._selected_set:
                    self._selected_items.append(item)
                    self._selected_set.add(item)
        else:
            try:
                if item in self._selected_set:
                    self._selected_items.remove(item)
                    self._selected_set.discard(item)
            except Exception:
                pass
        # move hover to this item if present
        try:
            for i, it in enumerate(list(getattr(self, '_items', []) or [])):
                if it is item:
                    self._hover_row = i
                    self._ensure_hover_visible()
                    break
        except Exception:
            pass

    def deleteAllItems(self):
        try:
            super().deleteAllItems()
        except Exception:
            self._items = []
        try:
            self._selected_items = []
            self._selected_set = set()
            self._hover_row = 0
            self._scroll_offset = 0
            self._current_visible_rows = None
            self._changed_item = None
        except Exception:
            pass

    def changedItem(self):
        return getattr(self, "_changed_item", None)

    def setVisible(self, visible: bool = True):
        super().setVisible(visible)
        # in curses backend visibility controls whether widget can receive focus
        self._can_focus = bool(visible)