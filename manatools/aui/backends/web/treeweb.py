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
from ...yui_common import YSelectionWidget, YTreeItem
from .commonweb import widget_attrs, escape_html


class YTreeWeb(YSelectionWidget):
    """Tree view widget rendered as a flat paginated table."""

    def __init__(self, parent=None, label: str = "", multiselection=False, recursiveselection=False):
        super().__init__(parent)
        self._label = label
        self._multiselection = multiselection
        self._recursiveselection = recursiveselection
        self._item_registry: dict = {}
        # Populated on every render(); maps DOM row index → YTreeItem
        self._flat_items: list = []
        self._logger = logging.getLogger(f"manatools.aui.web.{self.__class__.__name__}")

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
            self.selectItem(item, True)
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
        if not self._multiselection:
            self._selected_items.clear()
        self.selectItem(item, True)
        return item

    def _handle_selection_change(self, index: int, value: str = None):
        """Handle row click from the flat table rendering.

        The JS sends the absolute DOM row index (hidden rows included),
        which matches the position in self._flat_items built at render time.
        """
        if 0 <= index < len(self._flat_items):
            item = self._flat_items[index]
            if not self._multiselection:
                self._selected_items.clear()
            self.selectItem(item, True)

    def _set_backend_enabled(self, enabled: bool):
        self._notify_update()

    def setVisible(self, visible: bool = True):
        self._visible = bool(visible)
        self._notify_update()

    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self) -> str:
        self._logger.debug("render: %d root items", len(self._items))

        flat = self._flatten_items()

        # Rebuild registry and flat list on every full render so indices and
        # ids stay consistent after deleteAllItems() + re-population cycles.
        self._item_registry.clear()
        self._flat_items = []
        for item, _ in flat:
            item_id = self._item_id(item)
            self._item_registry[item_id] = item
            self._flat_items.append(item)
            if item.selected() and item not in self._selected_items:
                self.selectItem(item, True)

        max_depth = max((d for _, d in flat), default=0) + 1  # = number of columns

        # Outer wrapper: carries widget identity; adding mana-ytable activates
        # the shared table pagination/search JavaScript automatically.
        attrs = widget_attrs(self.id(), "YTree", True, self._visible, "mana-ytable")
        disabled_attr = ' disabled' if not self._enabled else ''

        # Controls bar — identical markup to tableweb
        controls = (
            '<div class="mana-table-controls">'
            '<label class="mana-table-length-label">'
            'Show\u00a0'
            f'<select class="form-select form-select-sm mana-table-pagesize"{disabled_attr}>'
            '<option value="10">10</option>'
            '<option value="25">25</option>'
            '<option value="50">50</option>'
            '<option value="100">100</option>'
            '<option value="-1">All</option>'
            '</select>'
            '\u00a0entries'
            '</label>'
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

        # Body: one row per item; label in the column matching its depth,
        # empty <td> cells for all other columns
        tbody = '<tbody>'
        for item, depth in flat:
            sel_class = ' selected' if item in self._selected_items else ''
            tbody += f'<tr class="mana-table-row{sel_class}">'
            for col in range(max_depth):
                if col == depth:
                    tbody += f'<td>{escape_html(item.label())}</td>'
                else:
                    tbody += '<td></td>'
            tbody += '</tr>'
        tbody += '</tbody>'

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
