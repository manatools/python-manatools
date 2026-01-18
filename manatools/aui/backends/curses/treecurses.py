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
import logging
from ...yui_common import *

# Module-level logger for tree curses backend
_mod_logger = logging.getLogger("manatools.aui.curses.tree.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)


class YTreeCurses(YSelectionWidget):
    """
    NCurses implementation of a tree widget.
    - Flattens visible nodes according to YTreeItem._is_open
    - Supports single/multi selection and recursive selection propagation
    - Preserves per-item selected() / setSelected() semantics and restores selections on rebuild
    - Keyboard: Up/Down/PageUp/PageDown/Home/End, SPACE = expand/collapse, ENTER = select/deselect
    """
    def __init__(self, parent=None, label="", multiselection=False, recursiveselection=False):
        super().__init__(parent)
        self._label = label
        self._multi = bool(multiselection)
        self._recursive = bool(recursiveselection)
        if self._recursive:
            self._multi = True
        self._immediate = self.notify()
        # Minimal height (items area) requested by this widget
        self._min_height = 6
        # Preferred height exposed to layout should include label line if any
        self._height = self._min_height + (1 if self._label else 0)
        self._can_focus = True
        self._focused = False
        self._hover_index = 0
        self._scroll_offset = 0
        self._visible_items = []
        self._selected_items = []
        self._last_selected_ids = set()
        self._suppress_selection_handler = False
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)
        # per-instance logger
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        # debuglabel: class and initial label
        try:
            self._logger.debug("%s.__init__ label=%s multiselection=%s recursive=%s", self.__class__.__name__, label, multiselection, recursiveselection)
        except Exception:
            pass

    def widgetClass(self):
        return "YTree"

    def hasMultiSelection(self):
        """Return True if the tree allows selecting multiple items at once."""
        return bool(self._multi)

    def immediateMode(self):
        return bool(self._immediate)

    def setImmediateMode(self, on:bool=True):
        self._immediate = on
        self.setNotify(on)

    def _create_backend_widget(self):
        try:
            # Keep preferred minimum for the layout (items + optional label)
            self._height = max(self._height, self._min_height + (1 if self._label else 0))
            # associate placeholder backend widget to avoid None
            self._backend_widget = self
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
            self._rebuildTree()
        except Exception as e:
            try:
                self._logger.critical("_create_backend_widget critical error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.critical("_create_backend_widget critical error: %s", e, exc_info=True)

    def addItem(self, item):
        """Ensure base storage gets the item and rebuild visible list immediately."""
        try:
            # prefer base implementation if present
            try:
                super().addItem(item)
            except Exception:
                # fallback: append to _items list used by this backend
                if not hasattr(self, "_items") or self._items is None:
                    self._items = []
                self._items.append(item)
        finally:
            try:
                # mark rebuild so new items are visible without waiting for external trigger
                self._rebuildTree()
            except Exception:
                pass

    def addItems(self, items):
        '''Add multiple items to the table. This is more efficient than calling addItem repeatedly.'''
        try:
            for item in items:
                # prefer base implementation if present
                try:
                    super().addItem(item)
                except Exception:
                    # fallback: append to _items list used by this backend
                    if not hasattr(self, "_items") or self._items is None:
                        self._items = []
                    self._items.append(item)
        finally:
            try:
                # mark rebuild so new items are visible without waiting for external trigger
                self._rebuildTree()
            except Exception:
                pass

    def removeItem(self, item):
        """Remove item from internal list and rebuild."""
        try:
            try:
                super().removeItem(item)
            except Exception:
                if hasattr(self, "_items") and item in self._items:
                    try:
                        self._items.remove(item)
                    except Exception:
                        pass
        finally:
            try:
                self._rebuildTree()
            except Exception:
                pass

    def deleteAllItems(self):
        """Clear model and all internal state for this tree."""
        self._suppress_selection_handler = True
        try:
            try:
                super().deleteAllItems()
            except Exception:
                self._items = []
        except Exception:
            pass
        # Reset selection and visibility state
        try:
            self._selected_items = []
            self._last_selected_ids = set()
            self._visible_items = []
            self._hover_index = 0
            self._scroll_offset = 0
        except Exception:
            pass
        try:
            # No items to show; nothing else to rebuild but ensure state consistent
            self._flatten_visible()
        except Exception:
            pass
        self._suppress_selection_handler = False

    def _collect_all_descendants(self, item):
        out = []
        stack = []
        try:
            for c in getattr(item, "_children", []) or []:
                stack.append(c)
        except Exception:
            pass
        while stack:
            cur = stack.pop()
            out.append(cur)
            try:
                for ch in getattr(cur, "_children", []) or []:
                    stack.append(ch)
            except Exception:
                pass
        return out

    def _clear_all_selected(self):
        """Clear the selected flag recursively across the entire tree."""
        try:
            roots = list(getattr(self, "_items", []) or [])
        except Exception:
            roots = []
        def _clear(nodes):
            for n in nodes:
                try:
                    n.setSelected(False)
                except Exception:
                    try:
                        setattr(n, "_selected", False)
                    except Exception:
                        pass
                try:
                    chs = callable(getattr(n, "children", None)) and n.children() or getattr(n, "_children", []) or []
                except Exception:
                    chs = getattr(n, "_children", []) or []
                if chs:
                    _clear(chs)
        _clear(roots)

    def _flatten_visible(self):
        """Produce self._visible_items = [(item, depth), ...] following _is_open flags."""
        self._visible_items = []
        def _visit(nodes, depth=0):
            for n in nodes:
                self._visible_items.append((n, depth))
                try:
                    is_open = bool(getattr(n, "_is_open", False))
                except Exception:
                    is_open = False
                if is_open:
                    try:
                        childs = callable(getattr(n, "children", None)) and n.children() or getattr(n, "_children", []) or []
                    except Exception:
                        childs = getattr(n, "_children", []) or []
                    if childs:
                        _visit(childs, depth + 1)
        roots = list(getattr(self, "_items", []) or [])
        _visit(roots, 0)

    def rebuildTree(self):
        """RebuildTree to maintain compatibility."""
        self._logger.warning("rebuildTree is deprecated and should not be needed anymore")
        self._rebuildTree()

    def _rebuildTree(self):
        """Recompute visible items and restore selection from item.selected() or last_selected_ids.

        Ensures ancestors of selected items are opened so selections are visible.
        """
        # preserve items selection if any
        self._suppress_selection_handler = True
        try:
            # collect all nodes and desired selected ids (from last ids or model flags)
            def _all_nodes(nodes):
                out = []
                for n in nodes:
                    out.append(n)
                    try:
                        chs = callable(getattr(n, "children", None)) and n.children() or getattr(n, "_children", []) or []
                    except Exception:
                        chs = getattr(n, "_children", []) or []
                    if chs:
                        out.extend(_all_nodes(chs))
                return out
            roots = list(getattr(self, "_items", []) or [])
            all_nodes = _all_nodes(roots)

            selected_ids = set(self._last_selected_ids) if self._last_selected_ids else set()
            if not selected_ids:
                for n in all_nodes:
                    try:
                        sel = False
                        if hasattr(n, "selected") and callable(getattr(n, "selected")):
                            sel = n.selected()
                        else:
                            sel = bool(getattr(n, "_selected", False))
                        if sel:
                            selected_ids.add(id(n))
                    except Exception:
                        pass

            # open ancestors for any selected node so it becomes visible
            if selected_ids:
                for n in list(all_nodes):
                    try:
                        if id(n) in selected_ids:
                            parent = None
                            try:
                                parent = n.parentItem() if callable(getattr(n, 'parentItem', None)) else getattr(n, '_parent_item', None)
                            except Exception:
                                parent = getattr(n, '_parent_item', None)
                            while parent:
                                try:
                                    try:
                                        parent.setOpen(True)
                                    except Exception:
                                        setattr(parent, '_is_open', True)
                                except Exception:
                                    pass
                                try:
                                    parent = parent.parentItem() if callable(getattr(parent, 'parentItem', None)) else getattr(parent, '_parent_item', None)
                                except Exception:
                                    break
                    except Exception:
                        pass

            # now recompute visible list based on possibly opened parents
            self._flatten_visible()

            # In single-selection mode, clamp desired selection to a single item.
            if selected_ids and not self._multi:
                chosen_id = None
                # Prefer a visible item
                for itm, _d in self._visible_items:
                    try:
                        if id(itm) in selected_ids:
                            chosen_id = id(itm)
                            break
                    except Exception:
                        pass
                if chosen_id is None:
                    try:
                        # fallback: arbitrary one
                        chosen_id = next(iter(selected_ids))
                    except Exception:
                        chosen_id = None
                selected_ids = {chosen_id} if chosen_id is not None else set()
            # collect from items' selected() property only (YTreeItem wins)
            selected_ids = set()
            try:
                def _collect_selected(nodes):
                    out = []
                    for n in nodes:
                        try:
                            sel = False
                            if hasattr(n, "selected") and callable(getattr(n, "selected")):
                                sel = n.selected()
                            else:
                                sel = bool(getattr(n, "_selected", False))
                            if sel:
                                out.append(n)
                        except Exception:
                            pass
                        try:
                            chs = callable(getattr(n, "children", None)) and n.children() or getattr(n, "_children", []) or []
                        except Exception:
                            chs = getattr(n, "_children", []) or []
                        if chs:
                            out.extend(_collect_selected(chs))
                    return out
                pre_selected = _collect_selected(list(getattr(self, "_items", []) or []))
                for p in pre_selected:
                    selected_ids.add(id(p))
            except Exception:
                pass
            # build logical selected list and last_selected_ids
            sel_items = []
            for itm, _d in self._visible_items:
                try:
                    if id(itm) in selected_ids:
                        sel_items.append(itm)
                except Exception:
                    pass
            # also include non-visible selected nodes (descendants) when tracking logic
            if selected_ids:
                for n in all_nodes:
                    if id(n) in selected_ids and n not in sel_items:
                        sel_items.append(n)
                # Ensure single-selection list contains only one item
                if not self._multi and len(sel_items) > 1:
                    # Prefer the visible one if present
                    visible_ids = {id(itm) for itm, _d in self._visible_items}
                    chosen = None
                    for it in sel_items:
                        if id(it) in visible_ids:
                            chosen = it
                            break
                    if chosen is None:
                        chosen = sel_items[0]
                    sel_items = [chosen]
            # apply selected flags to items consistently
            try:
                # clear all first
                def _clear(nodes):
                    for n in nodes:
                        try:
                            n.setSelected(False)
                        except Exception:
                            pass
                        try:
                            chs = callable(getattr(n, "children", None)) and n.children() or getattr(n, "_children", []) or []
                        except Exception:
                            chs = getattr(n, "_children", []) or []
                        if chs:
                            _clear(chs)
                _clear(list(getattr(self, "_items", []) or []))
            except Exception:
                pass
            for it in sel_items:
                try:
                    it.setSelected(True)
                except Exception:
                    pass
            self._selected_items = list(sel_items)
            self._last_selected_ids = set(id(i) for i in self._selected_items)
            # ensure hover_index valid
            if self._hover_index >= len(self._visible_items):
                self._hover_index = max(0, len(self._visible_items) - 1)
            self._ensure_hover_visible()
        except Exception:
            pass
        self._suppress_selection_handler = False

    def _ensure_hover_visible(self, height=None):
        """Adjust scroll offset so hover visible in given height area (if None use last draw height)."""
        try:
            # height param is number of rows available for items display (excluding label)
            if height is None:
                height = max(1, getattr(self, "_height", 1))
            visible = max(1, height)
            if self._hover_index < self._scroll_offset:
                self._scroll_offset = self._hover_index
            elif self._hover_index >= self._scroll_offset + visible:
                self._scroll_offset = self._hover_index - visible + 1
        except Exception:
            pass

    def _toggle_expand(self, item):
        try:
            self._suppress_selection_handler = True
        except Exception:
            pass
        try:
            try:
                cur = item.isOpen()
                item.setOpen(not cur)
            except Exception:
                try:
                    cur = bool(getattr(item, "_is_open", False))
                    item._is_open = not cur
                except Exception:
                    pass
            # preserve selected ids and rebuild
            try:
                self._last_selected_ids = set(id(i) for i in getattr(self, "_selected_items", []) or [])
            except Exception:
                self._last_selected_ids = set()
            self._rebuildTree()
        finally:
            try:
                self._suppress_selection_handler = False
            except Exception:
                pass

    def _handle_selection_action(self, item):
        """Toggle selection (ENTER) respecting multi/single & recursive semantics."""
        if item is None:
            return
        try:
            if self._multi:
                # toggle membership
                if item in self._selected_items:
                    # deselect item and (if recursive) descendants
                    if self._recursive:
                        to_remove = {item} | set(self._collect_all_descendants(item))
                        self._selected_items = [it for it in self._selected_items if it not in to_remove]
                        for it in to_remove:
                            try:
                                it.setSelected(False)
                            except Exception:
                                try:
                                    setattr(it, "_selected", False)
                                except Exception:
                                    pass
                    else:
                        try:
                            self._selected_items.remove(item)
                        except Exception:
                            pass
                        try:
                            item.setSelected(False)
                        except Exception:
                            try:
                                setattr(item, "_selected", False)
                            except Exception:
                                pass
                else:
                    # select item and possibly descendants
                    if self._recursive:
                        to_add = [item] + self._collect_all_descendants(item)
                        for it in to_add:
                            if it not in self._selected_items:
                                self._selected_items.append(it)
                                try:
                                    it.setSelected(True)
                                except Exception:
                                    try:
                                        setattr(it, "_selected", True)
                                    except Exception:
                                        pass
                    else:
                        self._selected_items.append(item)
                        try:
                            item.setSelected(True)
                        except Exception:
                            try:
                                setattr(item, "_selected", True)
                            except Exception:
                                pass
            else:
                # single selection: clear all flags recursively and set this one
                try:
                    self._clear_all_selected()
                except Exception:
                    pass
                self._selected_items = [item]
                try:
                    item.setSelected(True)
                except Exception:
                    try:
                        setattr(item, "_selected", True)
                    except Exception:
                        pass
        except Exception:
            pass

        # update last_selected_ids and notify
        try:
            self._last_selected_ids = set(id(i) for i in self._selected_items)
        except Exception:
            self._last_selected_ids = set()
        if self._immediate and self.notify():
            dlg = self.findDialog()
            if dlg:
                dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))

    def _draw(self, window, y, x, width, height):
        """Draw tree in provided rectangle. Expects height rows available."""
        try:
            # compute drawing area for items (first row may be label)
            line = y
            start_line = line
            label_rows = 1 if self._label else 0

            # Draw label
            if self._label:
                try:
                    window.addstr(line, x, self._label[:width], curses.A_BOLD)
                except curses.error:
                    pass
                line += 1

            # Actual rows given by parent for items
            available_rows = max(0, height - label_rows)
            # Keep _height as the current viewport rows (items area), not the preferred minimum
            self._height = max(1, available_rows)

            # record last draw height for navigation/ensure logic
            self._height = available_rows
            # rebuild visible items (safe cheap operation)
            self._flatten_visible()
            total = len(self._visible_items)
            if total == 0:
                try:
                    if available_rows > 0:
                        window.addstr(line, x, "(empty)", curses.A_DIM)
                except curses.error:
                    pass
                return

            # Clamp scroll/hover to the viewport
            self._ensure_hover_visible(height=self._height)

            # Draw only inside the allocated rectangle
            draw_rows = min(available_rows, max(0, total - self._scroll_offset))
            for i in range(draw_rows):
                idx = self._scroll_offset + i
                if idx >= total:
                    break
                itm, depth = self._visible_items[idx]
                is_selected = itm in self._selected_items
                # expander, text, attrs...
                try:
                    has_children = bool(getattr(itm, "_children", []) or (callable(getattr(itm, "children", None)) and (itm.children() or [])))
                except Exception:
                    has_children = False
                try:
                    is_open = bool(getattr(itm, "_is_open", False))
                except Exception:
                    is_open = False
                exp = "▾" if (has_children and is_open) else ("▸" if has_children else " ")
                checkbox = "*" if is_selected else " "
                indent = " " * (depth * 2)
                text = f"{indent}{exp} [{checkbox}] {itm.label()}"
                if len(text) > width:
                    text = text[:max(0, width - 1)] + "…"
                attr = curses.A_REVERSE if (self._focused and idx == self._hover_index and self.isEnabled()) else curses.A_NORMAL
                if not self.isEnabled():
                    attr |= curses.A_DIM
                try:
                    window.addstr(line + i, x, text.ljust(width), attr)
                except curses.error:
                    pass

            # Scroll indicators based on actual viewport rows
            try:
                if self._scroll_offset > 0 and available_rows > 0:
                    window.addch(y + label_rows, x + max(0, width - 1), '↑', curses.A_REVERSE)
                if (self._scroll_offset + available_rows) < total and available_rows > 0:
                    window.addch(y + label_rows + min(available_rows - 1, total - 1), x + max(0, width - 1), '↓', curses.A_REVERSE)
            except curses.error:
                pass
        except Exception:
            pass

    def _handle_key(self, key):
        """Keyboard handling: navigation, expand (SPACE), select (ENTER)."""
        if not self._focused or not self.isEnabled():
            return False
        handled = True
        total = len(self._visible_items)
        if key == curses.KEY_UP:
            if self._hover_index > 0:
                self._hover_index -= 1
                self._ensure_hover_visible(self._height)
        elif key == curses.KEY_DOWN:
            if self._hover_index < max(0, total - 1):
                self._hover_index += 1
                self._ensure_hover_visible(self._height)
        elif key == curses.KEY_PPAGE:
            step = max(1, self._height)
            self._hover_index = max(0, self._hover_index - step)
            self._ensure_hover_visible(self._height)
        elif key == curses.KEY_NPAGE:
            step = max(1, self._height)
            self._hover_index = min(max(0, total - 1), self._hover_index + step)
            self._ensure_hover_visible(self._height)
        elif key == curses.KEY_HOME:
            self._hover_index = 0
            self._ensure_hover_visible(self._height)
        elif key == curses.KEY_END:
            self._hover_index = max(0, total - 1)
            self._ensure_hover_visible(self._height)
        elif key in (ord(' '),):  # SPACE toggles expansion per dialog footer convention
            if 0 <= self._hover_index < total:
                itm, _ = self._visible_items[self._hover_index]
                # Toggle expand/collapse without changing selection
                self._toggle_expand(itm)
        elif key in (ord('\n'),):  # ENTER toggles selection
            if 0 <= self._hover_index < total:
                itm, _ = self._visible_items[self._hover_index]
                self._handle_selection_action(itm)
        else:
            handled = False
        return handled

    def currentItem(self):
        try:
            # Prefer explicit selected_items; if empty return hovered visible item (useful after selection)
            if self._selected_items:
                return self._selected_items[0]
            # fallback: return hovered visible item if any
            if 0 <= self._hover_index < len(getattr(self, "_visible_items", [])):
                return self._visible_items[self._hover_index][0]
            return None
        except Exception:
            return None

    def getSelectedItems(self):
        return list(self._selected_items)

    def selectItem(self, item, selected=True):
        """Programmatic select/deselect that respects recursive flag."""
        if item is None:
            return
        try:
            if selected:
                if not self._multi:
                    # clear others recursively and select only this one
                    try:
                        self._clear_all_selected()
                    except Exception:
                        pass
                    try:
                        item.setSelected(True)
                    except Exception:
                        try:
                            setattr(item, "_selected", True)
                        except Exception:
                            pass
                    self._selected_items = [item]
                else:
                    if item not in self._selected_items:
                        try:
                            item.setSelected(True)
                        except Exception:
                            try:
                                setattr(item, "_selected", True)
                            except Exception:
                                pass
                        self._selected_items.append(item)
                    if self._recursive:
                        for d in self._collect_all_descendants(item):
                            if d not in self._selected_items:
                                try:
                                    d.setSelected(True)
                                except Exception:
                                    try:
                                        setattr(d, "_selected", True)
                                    except Exception:
                                        pass
                                self._selected_items.append(d)
                # open parents so programmatically selected items are visible
                try:
                    parent = item.parentItem() if callable(getattr(item, 'parentItem', None)) else getattr(item, '_parent_item', None)
                except Exception:
                    parent = getattr(item, '_parent_item', None)
                while parent:
                    try:
                        try:
                            parent.setOpen(True)
                        except Exception:
                            setattr(parent, '_is_open', True)
                    except Exception:
                        pass
                    try:
                        parent = parent.parentItem() if callable(getattr(parent, 'parentItem', None)) else getattr(parent, '_parent_item', None)
                    except Exception:
                        break
            else:
                # deselect
                if item in self._selected_items:
                    try:
                        self._selected_items.remove(item)
                    except Exception:
                        pass
                try:
                    item.setSelected(False)
                except Exception:
                    try:
                        setattr(item, "_selected", False)
                    except Exception:
                        pass
                if self._recursive:
                    for d in self._collect_all_descendants(item):
                        if d in self._selected_items:
                            try:
                                self._selected_items.remove(d)
                            except Exception:
                                pass
                        try:
                            d.setSelected(False)
                        except Exception:
                            try:
                                setattr(d, "_selected", False)
                            except Exception:
                                pass
            # update last ids
            try:
                self._last_selected_ids = set(id(i) for i in self._selected_items)
            except Exception:
                self._last_selected_ids = set()
            # after programmatic selection, rebuild visible list to reflect opened parents
            try:
                self._rebuildTree()
            except Exception:
                pass
        except Exception:
            pass
