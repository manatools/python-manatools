# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
NCurses backend: YMenuBar implementation with keyboard navigation.
- Left/Right: switch top-level menus when focused
- Space: expand/collapse current menu
- Up/Down: navigate items when expanded
- Enter: activate item and emit YMenuEvent
'''
import curses
import logging
from ...yui_common import YWidget, YMenuEvent, YMenuItem


class YMenuBarCurses(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        self._menus = []  # list of YMenuItem (is_menu=True)
        self._focused = False
        self._can_focus = True
        self._expanded = False
        self._current_menu_index = 0
        self._current_item_index = 0
        self._height = 2  # one row for bar, one for dropdown baseline
        # For popup menu navigation: stack of menus and indices per level
        self._menu_path = []  # list of YMenuItem for current path (top menu -> submenus)
        self._menu_indices = []  # list of int current index per level
        # positions of top-level menu labels on the bar (start x)
        self._menu_positions = []
        # scrolling support: offsets per level and max visible rows
        self._scroll_offsets = []  # list of int per level for first visible item
        self._visible_rows_max = 8
        # remember last drawn bar geometry for overlay drawing
        self._bar_y = 0
        self._bar_x = 0
        self._bar_width = 0

    def widgetClass(self):
        return "YMenuBar"

    def addMenu(self, label: str = "", icon_name: str = "", menu: YMenuItem = None) -> YMenuItem:
        """Add a top-level menu by label or attach an existing YMenuItem.

        Mirrors the Qt/GTK signatures for parameter consistency.
        """
        m=None
        if menu is not None:
            if not menu.isMenu():
                raise ValueError("Provided YMenuItem is not a menu (is_menu=True)")
            m = menu
        else:
            if not label:
                raise ValueError("Menu label must be provided when no YMenuItem is given")
            m = YMenuItem(label, icon_name, enabled=True, is_menu=True)
        self._menus.append(m)
        return m

    def addItem(self, menu: YMenuItem, label: object, icon_name: str = "", enabled: bool = True) -> YMenuItem:
        """Add an item to a menu, accepting either a label or an existing YMenuItem.

        If `label` is a YMenuItem instance, attach it to `menu`. Otherwise,
        create a new item using the label and optional icon.
        """
        if isinstance(label, YMenuItem):
            item = label
            # attach to parent if not already
            try:
                setattr(item, "_parent", menu)
            except Exception:
                pass
            try:
                menu._children.append(item)
            except Exception:
                # fallback: use provided API if available
                try:
                    menu.addItem(item.label(), item.iconName())
                    item = menu._children[-1]
                except Exception:
                    raise
        else:
            item = menu.addItem(label, icon_name)
        try:
            item.setEnabled(enabled)
        except Exception:
            pass
        return item

    def setItemEnabled(self, item: YMenuItem, on: bool = True):
        item.setEnabled(on)
        # If current selection becomes disabled while expanded, move to next selectable
        try:
            if self._expanded and self._menu_path:
                cur_menu = self._menu_path[-1]
                idx = self._menu_indices[-1] if self._menu_indices else 0
                items = list(cur_menu._children)
                if 0 <= idx < len(items) and items[idx] == item and not item.enabled():
                    nxt = self._next_selectable_index(items, idx, +1)
                    if nxt is None:
                        nxt = self._next_selectable_index(items, idx, -1)
                    if nxt is not None:
                        self._menu_indices[-1] = nxt
        except Exception:
            pass

    def _path_for_item(self, item: YMenuItem) -> str:
        labels = []
        cur = item
        while cur is not None:
            labels.append(cur.label())
            cur = getattr(cur, "_parent", None)
        return "/".join(reversed(labels))

    def _emit_activation(self, item: YMenuItem):
        try:
            dlg = self.findDialog()
            if dlg and self.notify():
                dlg._post_event(YMenuEvent(item=item, id=self._path_for_item(item)))
        except Exception:
            pass

    def _is_separator(self, item: YMenuItem) -> bool:
        try:
            return item.isSeparator()
        except Exception:
            return False

    def _is_selectable(self, item: YMenuItem) -> bool:
        try:
            if self._is_separator(item):
                return False
            return bool(item.enabled())
        except Exception:
            return False

    def _first_selectable_index(self, items):
        for i, it in enumerate(items):
            if self._is_selectable(it):
                return i
        return None

    def _next_selectable_index(self, items, start_idx, direction):
        """Return next selectable index from start_idx stepping by direction; None if none."""
        if not items:
            return None
        if direction > 0:
            rng = range(start_idx + 1, len(items))
        else:
            rng = range(start_idx - 1, -1, -1)
        for i in rng:
            it = items[i]
            if self._is_selectable(it):
                return i
        return None

    def _draw(self, window, y, x, width, height):
        try:
            # remember bar area
            self._bar_y = y
            self._bar_x = x
            self._bar_width = width
            # draw menubar on first line
            bar_attr = curses.A_REVERSE if self._focused else curses.A_NORMAL
            cx = x
            # reset menu positions
            self._menu_positions = []
            for idx, menu in enumerate(self._menus):
                label = f" {menu.label()} "
                attr = bar_attr
                if idx == self._current_menu_index:
                    attr |= curses.A_BOLD
                try:
                    # record start position for this menu label (keep index alignment)
                    try:
                        if not menu.visible():
                            # keep alignment with None placeholder
                            self._menu_positions.append(None)
                            cx += len(label)
                            if cx >= x + width:
                                break
                            continue
                    except Exception:
                        pass
                    self._menu_positions.append(cx)
                    window.addstr(y, cx, label[:max(0, width - (cx - x))], attr)
                except curses.error:
                    self._menu_positions.append(cx)
                    pass
                cx += len(label)
                if cx >= x + width:
                    break
            # dropdown area: drawn in _draw_expanded_list by dialog to ensure overlay on top
        except curses.error:
            pass

    def _draw_expanded_list(self, window):
        """Draw expanded popups on top of other widgets (overlay), similar to combobox."""
        if not self._expanded or not (0 <= self._current_menu_index < len(self._menus)):
            return
        try:
            # Start with top-level menu position, relative to dialog
            try:
                if self._current_menu_index < len(self._menu_positions):
                    pos = self._menu_positions[self._current_menu_index]
                    start_x = pos if pos is not None else self._bar_x
                else:
                    start_x = self._bar_x
            except Exception:
                start_x = self._bar_x
            popup_x = start_x
            popup_y = self._bar_y + 1
            # ensure menu_path initialized
            if not self._menu_path:
                self._menu_path = [self._menus[self._current_menu_index]]
                self._menu_indices = [0]
                self._scroll_offsets = [0]
            for level, menu in enumerate(self._menu_path):
                # only visible children
                items = [it for it in list(menu._children) if getattr(it, 'visible', lambda: True)()]
                # compute width for this popup
                max_label = 0
                for it in items:
                    txt = it.label()
                    if it.isMenu():
                        txt = txt + " ►"
                    if len(txt) > max_label:
                        max_label = len(txt)
                popup_width = max(10, max_label + 4)
                # check screen bounds
                screen_h, screen_w = window.getmaxyx()
                if popup_x + popup_width >= screen_w:
                    popup_x = max(0, start_x - popup_width)
                # compute visible rows; draw above if not enough space below
                available_rows_below = max(1, screen_h - (popup_y) - 1)
                visible_rows = min(len(items), min(self._visible_rows_max, available_rows_below))
                if popup_y + visible_rows >= screen_h:
                    popup_y = max(1, self._bar_y - visible_rows)
                    visible_rows = min(len(items), min(self._visible_rows_max, popup_y))
                # ensure scroll_offsets entry
                if level >= len(self._scroll_offsets):
                    self._scroll_offsets.append(0)
                # keep selection visible
                sel_idx = self._menu_indices[level] if level < len(self._menu_indices) else 0
                offset = self._scroll_offsets[level]
                if sel_idx < offset:
                    offset = sel_idx
                if sel_idx >= offset + visible_rows:
                    offset = max(0, sel_idx - visible_rows + 1)
                self._scroll_offsets[level] = offset
                # opaque background
                try:
                    for i in range(visible_rows):
                        bg = " " * popup_width
                        window.addstr(popup_y + i, popup_x, bg[:popup_width], curses.A_NORMAL)
                    # optional separator line above
                except curses.error:
                    pass
                # visible items slice
                vis_items = items[offset:offset + visible_rows]
                for i, item in enumerate(vis_items):
                    real_i = offset + i
                    # separators are drawn as a centered line of underscores
                    if self._is_separator(item):
                        try:
                            us_count = max(1, popup_width - 2)
                            pad = max(0, (popup_width - us_count) // 2)
                            sep_text = (" " * pad) + ("–" * us_count)
                            sep_text = sep_text.ljust(popup_width)[:popup_width]
                            window.addstr(popup_y + i, popup_x, sep_text, curses.A_NORMAL)
                        except curses.error:
                            pass
                        continue
                    sel = (self._menu_indices[level] == real_i) if level < len(self._menu_indices) else (i == 0)
                    prefix = "* " if sel else "  "
                    label_text = item.label()
                    marker = " ►" if item.isMenu() else ""
                    text = prefix + label_text + marker
                    attr = curses.A_REVERSE if sel else curses.A_NORMAL
                    if not item.enabled():
                        attr |= curses.A_DIM
                    try:
                        window.addstr(popup_y + i, popup_x, text.ljust(popup_width)[:popup_width], attr)
                    except curses.error:
                        pass
                # scroll indicators
                try:
                    if self._scroll_offsets[level] > 0 and visible_rows > 0:
                        window.addstr(popup_y, popup_x + popup_width - 1, "▲")
                except curses.error:
                    pass
                try:
                    if self._scroll_offsets[level] + visible_rows < len(items) and visible_rows > 0:
                        window.addstr(popup_y + visible_rows - 1, popup_x + popup_width - 1, "▼")
                except curses.error:
                    pass
                # next level to right
                popup_x = popup_x + popup_width + 1
                if level + 1 >= len(self._menu_path):
                    break
        except curses.error:
            pass

    def _prev_visible_menu_index(self, start_idx):
        for i in range(start_idx - 1, -1, -1):
            try:
                if self._menus[i].visible():
                    return i
            except Exception:
                # assume visible if error
                return i
        return None

    def _next_visible_menu_index(self, start_idx):
        for i in range(start_idx + 1, len(self._menus)):
            try:
                if self._menus[i].visible():
                    return i
            except Exception:
                return i
        return None

    def rebuildMenus(self):
        """Rebuild all menus for curses backend.

        There are no native widgets per-menu; reset transient caches and
        request a dialog redraw to reflect model changes.
        """
        try:
            # reset transient layout caches
            self._menu_positions = []
            self._menu_path = []
            self._menu_indices = []
            self._scroll_offsets = []
            # request dialog redraw
            try:
                dlg = self.findDialog()
                if dlg is not None:
                    dlg._last_draw_time = 0
            except Exception:
                pass
        except Exception:
            try:
                self._logger.exception("rebuildMenus failed for curses backend")
            except Exception:
                pass

    # Backward compatibility shim
    def rebuildMenu(self, menu: YMenuItem = None):
        # adjust current menu index if a specific menu becomes invisible
        try:
            if menu is not None and hasattr(menu, 'isMenu') and menu.isMenu():
                try:
                    if not menu.visible():
                        if menu in self._menus and self._menus.index(menu) == self._current_menu_index:
                            nxt = self._next_visible_menu_index(self._current_menu_index)
                            if nxt is None:
                                prv = self._prev_visible_menu_index(self._current_menu_index)
                                if prv is not None:
                                    self._current_menu_index = prv
                            else:
                                self._current_menu_index = nxt
                except Exception:
                    pass
        except Exception:
            pass
        self.rebuildMenus()

    def deleteMenus(self):
        """Clear all menus and reset transient state, then request redraw."""
        try:
            try:
                self._menus.clear()
            except Exception:
                self._menus = []
            # reset indices and caches
            self._expanded = False
            self._current_menu_index = 0
            self._current_item_index = 0
            self._menu_positions = []
            self._menu_path = []
            self._menu_indices = []
            self._scroll_offsets = []
            # request redraw
            try:
                dlg = self.findDialog()
                if dlg is not None:
                    dlg._last_draw_time = 0
            except Exception:
                pass
        except Exception:
            try:
                self._logger.exception("deleteMenus failed for curses backend")
            except Exception:
                pass

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled():
            return False
        handled = True
        if key in (curses.KEY_LEFT, ord('h')):
            if self._expanded:
                # go up one level if possible, otherwise move to previous top-level menu
                if len(self._menu_path) > 1:
                    self._menu_path.pop()
                    self._menu_indices.pop()
                else:
                    prev = self._prev_visible_menu_index(self._current_menu_index)
                    if prev is not None:
                        self._current_menu_index = prev
                        # reset path to new top menu
                        self._menu_path = [self._menus[self._current_menu_index]]
                        self._menu_indices = [0]
                        self._scroll_offsets = [0]
            else:
                prev = self._prev_visible_menu_index(self._current_menu_index)
                if prev is not None:
                    self._current_menu_index = prev
        elif key in (curses.KEY_RIGHT, ord('l')):
            if self._expanded:
                # try to descend into submenu if selected item is a menu
                cur_menu = self._menu_path[-1]
                idx = self._menu_indices[-1] if self._menu_indices else 0
                items = [it for it in list(cur_menu._children) if getattr(it, 'visible', lambda: True)()]
                if 0 <= idx < len(items) and items[idx].isMenu():
                    self._menu_path.append(items[idx])
                    self._menu_indices.append(0)
                else:
                    # otherwise move to next top-level menu
                    nxt = self._next_visible_menu_index(self._current_menu_index)
                    if nxt is not None:
                        self._current_menu_index = nxt
                        self._menu_path = [self._menus[self._current_menu_index]]
                        self._menu_indices = [0]
                        self._scroll_offsets = [0]
            else:
                nxt = self._next_visible_menu_index(self._current_menu_index)
                if nxt is not None:
                    self._current_menu_index = nxt
        elif key in (ord(' '), curses.KEY_DOWN):
            # expand
            if not self._expanded:
                self._expanded = True
                # initialize path to current top menu
                if 0 <= self._current_menu_index < len(self._menus):
                    # ensure current top menu is visible; if not find next visible
                    try:
                        if not self._menus[self._current_menu_index].visible():
                            nxt = self._next_visible_menu_index(self._current_menu_index)
                            if nxt is not None:
                                self._current_menu_index = nxt
                    except Exception:
                        pass
                    self._menu_path = [self._menus[self._current_menu_index]]
                    # start at first selectable item
                    items = list(self._menu_path[0]._children)
                    first = self._first_selectable_index(items)
                    if first is None:
                        # no selectable items -> keep expanded false
                        self._expanded = False
                        self._menu_path = []
                        self._menu_indices = []
                        self._scroll_offsets = []
                        return True
                    self._menu_indices = [first]
                    self._scroll_offsets = [0]
            else:
                # move down in current popup
                cur_idx = self._menu_indices[-1]
                cur_menu = self._menu_path[-1]
                items = [it for it in list(cur_menu._children) if getattr(it, 'visible', lambda: True)()]
                if items:
                    nxt = self._next_selectable_index(items, cur_idx, +1)
                    if nxt is not None:
                        self._menu_indices[-1] = nxt
                        # adjust scroll offset
                        level = len(self._menu_indices) - 1
                        visible_rows = self._visible_rows_max
                        offset = self._scroll_offsets[level] if level < len(self._scroll_offsets) else 0
                        if nxt >= offset + visible_rows:
                            self._scroll_offsets[level] = max(0, nxt - visible_rows + 1)
        elif key == curses.KEY_UP:
            if self._expanded:
                cur_idx = self._menu_indices[-1]
                cur_menu = self._menu_path[-1]
                items = list(cur_menu._children)
                if items:
                    # If at first selectable item on top-level, collapse to menubar
                    first = self._first_selectable_index(items)
                    level = len(self._menu_indices) - 1
                    if level == 0 and first is not None and cur_idx == first:
                        self._expanded = False
                        self._menu_path = []
                        self._menu_indices = []
                        self._scroll_offsets = []
                        return True
                    prev = self._next_selectable_index(items, cur_idx, -1)
                    if prev is not None:
                        self._menu_indices[-1] = prev
                        visible_rows = self._visible_rows_max
                        offset = self._scroll_offsets[level] if level < len(self._scroll_offsets) else 0
                        if prev < offset:
                            self._scroll_offsets[level] = prev
        elif key == curses.KEY_NPAGE:
            # page down
            if self._expanded and self._menu_path:
                level = len(self._menu_indices) - 1
                cur_menu = self._menu_path[-1]
                total = len(cur_menu._children)
                visible_rows = self._visible_rows_max
                # advance through selectable items
                idx = self._menu_indices[-1]
                items = list(cur_menu._children)
                steps = visible_rows
                while steps > 0:
                    nxt = self._next_selectable_index(items, idx, +1)
                    if nxt is None:
                        break
                    idx = nxt
                    steps -= 1
                self._menu_indices[-1] = idx
                offset = self._scroll_offsets[level]
                self._scroll_offsets[level] = min(max(0, total - visible_rows), max(offset, idx - visible_rows + 1))
        elif key == curses.KEY_PPAGE:
            # page up
            if self._expanded and self._menu_path:
                level = len(self._menu_indices) - 1
                cur_menu = self._menu_path[-1]
                visible_rows = self._visible_rows_max
                idx = self._menu_indices[-1]
                items = list(cur_menu._children)
                steps = visible_rows
                while steps > 0:
                    prv = self._next_selectable_index(items, idx, -1)
                    if prv is None:
                        break
                    idx = prv
                    steps -= 1
                self._menu_indices[-1] = idx
                offset = self._scroll_offsets[level]
                self._scroll_offsets[level] = min(offset, idx)
        elif key in (curses.KEY_ENTER, 10, 13):
            if self._expanded:
                cur_menu = self._menu_path[-1]
                idx = self._menu_indices[-1]
                items = [it for it in list(cur_menu._children) if getattr(it, 'visible', lambda: True)()]
                if 0 <= idx < len(items):
                    item = items[idx]
                    if item.isMenu() and item.enabled():
                        # descend
                        self._menu_path.append(item)
                        self._menu_indices.append(0)
                        self._scroll_offsets.append(0)
                    else:
                        if item.enabled():
                            self._emit_activation(item)
                            # collapse after activation
                            self._expanded = False
                            self._menu_path = []
                            self._menu_indices = []
                            self._scroll_offsets = []
        elif key in (27, ord('q')):
            # collapse menus
            self._expanded = False
            self._menu_path = []
            self._menu_indices = []
            self._scroll_offsets = []
        else:
            handled = False
        return handled
