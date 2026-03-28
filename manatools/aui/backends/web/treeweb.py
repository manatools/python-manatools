"""
Web backend Tree implementation.
Author: Matteo Pasotti <xquiet@coriolite.com>
License: LGPLv2+
"""
import logging
from ...yui_common import YSelectionWidget, YTreeItem
from .commonweb import widget_attrs, escape_html


class YTreeWeb(YSelectionWidget):
    """Tree view widget."""

    def __init__(self, parent=None, label: str = "", multiselection=False, recursiveselection=False):
        super().__init__(parent)
        self._label = label
        self._multiselection = multiselection
        self._recursiveselection = recursiveselection
        self._item_registry: dict = {}
        self._logger = logging.getLogger(f"manatools.aui.web.{self.__class__.__name__}")

    def widgetClass(self):
        return "YTree"

    def addItem(self, item, notify=True):
        """Add a root-level item and register its entire subtree."""
        if isinstance(item, str):
            item = YTreeItem(item)
        elif not isinstance(item, YTreeItem):
            raise TypeError(f"YTreeWeb.addItem expects a YTreeItem or string, got {type(item)}")
        # Use super() so YSelectionWidget can maintain its own bookkeeping
        # (parent refs, index, internal lists) — same as Qt backend.
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
        """Recursively register item and all its descendants.

        Also honours pre-selected state set by the caller before addItem().
        """
        self._item_registry[self._item_id(item)] = item
        if item.selected():
            self.selectItem(item, True)
        if item.hasChildren():
            for child in item.childrenBegin():
                self._register_item_tree(child)

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
        """Called by the dialog event dispatcher when a tree item is clicked.

        Updates internal selection state and returns the clicked YTreeItem,
        or None if the id is unknown.
        """
        item = self._item_registry.get(item_id)
        if item is None:
            return None
        if not self._multiselection:
            self._selected_items.clear()
        self.selectItem(item, True)
        return item

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

    def _render_item(self, item: YTreeItem, level: int = 0) -> str:
        indent = level * 20
        item_id = self._item_id(item)
        selected_class = "selected" if item in self._selected_items else ""
        open_class = "open" if item.isOpen() else "collapsed"

        children_html = ""
        if item.hasChildren():
            for child in item.childrenBegin():
                children_html += self._render_item(child, level + 1)

        children_block = (
            f'<div class="mana-tree-children">{children_html}</div>'
            if children_html else ""
        )

        return (
            f'<div class="mana-tree-item {selected_class} {open_class}"'
            f' style="padding-left:{indent}px"'
            f' data-level="{level}"'
            f' data-item-id="{item_id}"'
            f' data-tree-id="{self.id()}">'
            f'<span class="mana-tree-toggle"></span>'
            f'<span class="mana-tree-label">{escape_html(item.label())}</span>'
            f'{children_block}'
            f'</div>'
        )

    def render(self) -> str:
        self._logger.debug("render: %d root items", len(self._items))
        # Rebuild registry on every full render so ids stay consistent after
        # deleteAllItems() + re-population cycles.
        self._item_registry.clear()
        for item in self._items:
            self._register_item_tree(item)

        label_html = ""
        if self._label:
            label_html = (
                f'<label class="mana-tree-label">'
                f'{escape_html(self._label)}'
                f'</label>'
            )

        items_html = "".join(self._render_item(item) for item in self._items)
        attrs = widget_attrs(self.id(), "YTree", self._enabled, self._visible)

        return (
            f'<div class="mana-tree-container" data-container-for="{self.id()}">'
            f'{label_html}'
            f'<div {attrs}>{items_html}</div>'
            f'</div>'
        )
