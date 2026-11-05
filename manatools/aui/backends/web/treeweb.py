"""
Web backend Tree implementation.
Author: Matteo Pasotti <xquiet@coriolite.com>
License: LGPLv2+

The tree is rendered as a paginated, searchable flat table where each
depth level occupies a separate column (root items in col 1, their
children in col 2, grandchildren in col 3, …).  This reuses the
mana-ytable HTML structure so the client-side pagination and search
JavaScript activates automatically, with no changes to dnfdragora or
the public YUI API.
"""
import logging
from ...yui_common import YSelectionWidget, YTreeItem, YWidgetEvent, YEventReason
from .commonweb import widget_attrs, escape_html, escape_attr


class YTreeWeb(YSelectionWidget):
    """Tree view widget rendered as a flat paginated table."""

    def __init__(self, parent=None, label: str = "", multiselection=False, recursiveselection=False):
        self._multiselection = multiselection
        self._recursiveselection = recursiveselection
        self._item_registry: dict = {}
        # Populated on every render(); maps DOM row index → YTreeItem
        self._flat_items: list = []
        # (item, depth) pairs of the last render, in DOM row order
        self._flat_rows: list = []
        self._logger = logging.getLogger(f"manatools.aui.web.{self.__class__.__name__}")
        super().__init__(parent)
        # YSelectionWidget.__init__ resets _label, so set it afterwards.
        self._label = label

    def widgetClass(self):
        return "YTree"

    def addItem(self, item, notify=True):
        """Add a root-level item and register its entire subtree."""
        if isinstance(item, str):
            item = YTreeItem(item)
        elif not isinstance(item, YTreeItem):
            raise TypeError(f"YTreeWeb.addItem expects a YTreeItem or string, got {type(item)}")
        super().addItem(item)
        try:
            item.setIndex(len(self._items) - 1)
        except Exception:
            pass
        self._register_item_tree(item)
        self._logger.debug("addItem: added %r, total root items: %d", item.label(), len(self._items))
        if notify:
            self._notify_update()
        return item

    def addItems(self, items):
        """Add multiple root-level items with a single deferred UI update."""
        for item in items:
            if isinstance(item, str):
                item = YTreeItem(item)
            elif not isinstance(item, YTreeItem):
                raise TypeError(f"YTreeWeb.addItems expects YTreeItem or string, got {type(item)}")
            super().addItem(item)
            try:
                item.setIndex(len(self._items) - 1)
            except Exception:
                pass
            self._register_item_tree(item)
        self._notify_update()

    def deleteAllItems(self):
        """Clear all items, selections and the registry, then refresh the UI."""
        try:
            super().deleteAllItems()
        except Exception:
            self._items = []
            self._selected_items = []
        self._item_registry.clear()
        self._flat_items = []
        self._flat_rows = []
        self._notify_update()

    def rebuildTree(self):
        self._notify_update()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _item_id(self, item: YTreeItem) -> str:
        """Return a stable DOM-safe id string for a YTreeItem."""
        return f"{self.id()}-item-{id(item)}"

    def _register_item_tree(self, item: YTreeItem):
        """Recursively register item and all its descendants."""
        self._item_registry[self._item_id(item)] = item
        if item.selected():
            self._select_model(item, True)
        if item.hasChildren():
            for child in item.childrenBegin():
                self._register_item_tree(child)

    def _flatten_items(self) -> list:
        """DFS pre-order traversal returning [(item, depth), ...]."""
        result = []

        def visit(item, depth):
            result.append((item, depth))
            if item.hasChildren():
                for child in item.childrenBegin():
                    visit(child, depth + 1)

        for root in self._items:
            visit(root, 0)
        return result

    def currentItem(self):
        """Return the first selected item, or None."""
        return self._selected_items[0] if self._selected_items else None

    def _select_model(self, item, selected: bool = True) -> bool:
        """Update selection state without re-rendering; True if it changed.

        Single selection replaces the current item and clears the old item's
        flag.  The flat table shows every item, so open state is not touched.
        """
        before = list(self._selected_items)
        if selected:
            if self._multiselection:
                if item not in self._selected_items:
                    self._selected_items.append(item)
            else:
                for old in self._selected_items:
                    if old is not item:
                        old.setSelected(False)
                self._selected_items = [item]
        elif item in self._selected_items:
            self._selected_items.remove(item)
        try:
            item.setSelected(bool(selected))
        except Exception:
            pass
        return self._selected_items != before

    def selectItem(self, item, selected: bool = True):
        """Select or deselect *item* and show it in the browser."""
        if self._select_model(item, selected):
            self._notify_update()

    def activate(self) -> bool:
        """Post an Activated event for the current item, as a double click would."""
        if self.currentItem() is None:
            return False
        dialog = self.findDialog()
        if dialog is not None and self.notify():
            dialog._post_event(YWidgetEvent(self, YEventReason.Activated))
        return True

    def setProperty(self, propertyName: str, val) -> bool:
        if propertyName == "immediateMode":
            self.setImmediateMode(bool(val))
            return True
        return False

    def getProperty(self, propertyName: str):
        if propertyName == "immediateMode":
            return self.immediateMode()
        return None

    def hasMultiSelection(self) -> bool:
        return bool(self._multiselection)

    def immediateMode(self) -> bool:
        return bool(self._notify)

    def setImmediateMode(self, on: bool = True):
        self._notify = bool(on)
        self.setNotify(on)

    def _handle_item_click(self, item_id: str):
        """Legacy handler kept for API compatibility.

        Called by dialogweb when an event carries 'itemId' (old tree HTML).
        With the new table rendering this path is not taken, but it remains
        so that any code still producing itemId events continues to work.
        """
        item = self._item_registry.get(item_id)
        if item is None:
            return None
        self._select_model(item, True)
        return item

    def _handle_selection_change(self, index: int, value: str = None):
        """Handle row click from the flat table rendering.

        The JS sends the absolute DOM row index (hidden rows included),
        which matches the position in self._flat_items built at render time.
        """
        if 0 <= index < len(self._flat_items):
            self._select_model(self._flat_items[index], True)

    def _context_menu_select(self, ref):
        """Context-menu adapter: right-click on a row.

        *ref* is the absolute DOM row index (flat table rendering) or an item
        id string.  An unselected item becomes the only selected one, so the
        handler can rely on selectedItem(); an item inside the selection keeps
        it.  Only the rows are pushed, so the page/filter state is kept.
        Runs on a server thread: it resolves *ref* against the snapshot of the
        last render and never rebuilds it.
        """
        if isinstance(ref, str):
            item = getattr(self, "_item_registry", {}).get(ref)
        elif isinstance(ref, int):
            flat_items = getattr(self, "_flat_items", [])
            item = flat_items[ref] if 0 <= ref < len(flat_items) else None
        else:
            item = None
        if item is None or item in self._selected_items:
            return
        for old in list(self._selected_items):
            try:
                old.setSelected(False)
            except Exception:
                pass
        try:
            item.setSelected(True)
        except Exception:
            pass
        self._selected_items = [item]
        dialog = self.findDialog()
        if dialog is None or not hasattr(dialog, "_broadcast"):
            return
        dialog._broadcast({"type": "update", "updates": [{
            "action": "rows", "target": f"#{self.id()}", "html": self._render_rows_html(),
        }]})

    def _context_menu_notify_changed(self):
        self._notify_update()

    def _set_backend_enabled(self, enabled: bool):
        self._notify_update()

    def setVisible(self, visible: bool = True):
        self._visible = bool(visible)
        self._notify_update()

    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)

    def setHelpText(self, help_text: str):
        super().setHelpText(help_text)
        self._notify_update()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _sync_flat_items(self) -> list:
        """Flatten the items and rebuild the registry and the flat row list.

        Done on every full render so indices and ids stay consistent after
        deleteAllItems() + re-population cycles.  The new lists are built
        aside and swapped in whole, so readers on other threads always see a
        complete snapshot.
        """
        flat = self._flatten_items()
        registry = {}
        flat_items = []
        for item, _ in flat:
            registry[self._item_id(item)] = item
            flat_items.append(item)
            if item.selected() and item not in self._selected_items:
                self._select_model(item, True)
        self._item_registry = registry
        self._flat_items = flat_items
        self._flat_rows = flat
        return flat

    def _render_rows_html(self, flat=None) -> str:
        """Return the inner HTML of <tbody>: one row per item, label in the
        column matching its depth, empty <td> cells for all other columns.

        Without *flat* the rows of the last render are used as they are: the
        caller may run on a server thread and must not rebuild the model.
        """
        if flat is None:
            flat = getattr(self, "_flat_rows", [])
        max_depth = max((d for _, d in flat), default=0) + 1
        selected = list(self._selected_items)
        rows = []
        for item, depth in flat:
            sel_class = ' selected' if item in selected else ''
            cells = ''.join(
                f'<td>{escape_html(item.label())}</td>' if col == depth else '<td></td>'
                for col in range(max_depth)
            )
            rows.append(f'<tr class="mana-table-row{sel_class}">{cells}</tr>')
        return ''.join(rows)

    def render(self) -> str:
        self._logger.debug("render: %d root items", len(self._items))

        flat = self._sync_flat_items()
        max_depth = max((d for _, d in flat), default=0) + 1  # = number of columns

        # Outer wrapper: carries widget identity; adding mana-ytable activates
        # the shared table pagination/search JavaScript automatically.
        attrs = widget_attrs(self.id(), "YTree", True, self._visible, "mana-ytable", {
            "data-notify-context-menu": "1" if self.notifyContextMenu() else None})
        # Tooltip on the wrapper: rows are rebuilt by JS (deferred push,
        # pagination), so a per-row title would be lost.
        if self.helpText():
            attrs += f' title="{escape_attr(self.helpText())}"'
        disabled_attr = ' disabled' if not self._enabled else ''

        # Controls bar: search input only (page-size selector omitted)
        controls = (
            '<div class="mana-table-controls">'
            f'<input type="search" class="form-control form-control-sm mana-table-search"'
            f' placeholder="Search\u2026" aria-label="Search"{disabled_attr}>'
            '</div>'
        )

        # Header: tree label in column 0, remaining depth-level columns empty
        thead = '<thead><tr>'
        thead += f'<th scope="col">{escape_html(self._label) if self._label else ""}</th>'
        for _ in range(max_depth - 1):
            thead += '<th scope="col"></th>'
        thead += '</tr></thead>'

        tbody = f'<tbody>{self._render_rows_html(flat)}</tbody>'

        scroll = (
            '<div class="mana-table-scroll">'
            '<table class="table table-sm table-hover mana-table-inner">'
            f'{thead}{tbody}'
            '</table>'
            '</div>'
        )

        footer = (
            '<div class="mana-table-footer">'
            '<span class="mana-table-info"></span>'
            '<nav aria-label="Table navigation">'
            '<ul class="pagination pagination-sm mb-0 mana-table-pagination"></ul>'
            '</nav>'
            '</div>'
        )

        return f'<div {attrs}>{controls}{scroll}{footer}</div>'
