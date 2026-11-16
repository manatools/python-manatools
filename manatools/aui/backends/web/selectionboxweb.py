"""
Web backend SelectionBox implementation.
"""

from ...yui_common import YSelectionWidget
from .commonweb import widget_attrs, escape_html, format_label_with_shortcut


class YSelectionBoxWeb(YSelectionWidget):
    """List selection box widget."""
    
    def __init__(self, parent=None, label: str = "", multi_selection: bool = False):
        self._multi_selection = multi_selection
        super().__init__(parent)
        # YSelectionWidget.__init__ resets _label, so set it afterwards.
        self._label = label

    def label(self) -> str:
        return self._label

    def setLabel(self, label: str):
        self._label = label
        self._notify_update()

    def multiSelection(self) -> bool:
        return bool(self._multi_selection)

    def setMultiSelection(self, enabled: bool):
        """Switch between single and multi selection; leaving multi selection
        keeps only the first selected item, as on Qt."""
        self._multi_selection = bool(enabled)
        if not self._multi_selection and len(self._selected_items) > 1:
            for item in self._selected_items[1:]:
                item.setSelected(False)
            self._selected_items = self._selected_items[:1]
        self._notify_update()

    def selectedItems(self):
        return self._selected_items

    def selectItem(self, item, selected: bool = True):
        """Select or deselect *item* and show it in the browser."""
        if item not in self._items:
            return
        if self._multi_selection:
            if selected and item not in self._selected_items:
                self._selected_items.append(item)
            elif not selected and item in self._selected_items:
                self._selected_items.remove(item)
        else:
            for old in self._selected_items:
                if old is not item:
                    old.setSelected(False)
            self._selected_items = [item] if selected else []
        item.setSelected(bool(selected))
        self._notify_update()

    def deleteAllItems(self):
        super().deleteAllItems()
        self._notify_update()
    
    def widgetClass(self):
        return "YSelectionBox"
    
    def value(self) -> str:
        """Return the label of the first selected item, or empty string."""
        return self._selected_items[0].label() if self._selected_items else ""

    def addItem(self, item, notify=True):
        """Add an item and optionally push a UI update."""
        super().addItem(item)
        # Honor pre-selected state set by the caller before addItem().
        if hasattr(item, 'selected') and item.selected():
            if item not in self._selected_items:
                if not self._multi_selection:
                    self._selected_items = [item]
                else:
                    self._selected_items.append(item)
        if notify:
            self._notify_update()
        return item

    def _handle_selection_change(self, indices, value=None):
        """Handle selection change from browser.

        dialogweb passes (selectedIndex, selectedValue); a selection box sends
        the list of selected option indices and no value.
        """
        if isinstance(indices, int):
            indices = [indices]
        
        self._selected_items = []
        for idx, item in enumerate(self._items):
            chosen = idx in indices
            item.setSelected(chosen)
            if chosen:
                self._selected_items.append(item)
    
    def _context_menu_select(self, ref):
        """Context-menu adapter: right-click on option *ref* (its value index).

        An unselected option becomes the only selected one, so the handler can
        rely on selectedItem(); an option inside the selection keeps it.
        """
        items = getattr(self, "_items", [])
        if not isinstance(ref, int) or not (0 <= ref < len(items)):
            return
        item = items[ref]
        if item in self._selected_items:
            return
        for old in self._selected_items:
            old.setSelected(False)
        item.setSelected(True)
        self._selected_items = [item]
        self._notify_update()

    def _context_menu_notify_changed(self):
        self._notify_update()

    def _set_backend_enabled(self, enabled: bool):
        self._notify_update()

    def setHelpText(self, help_text: str):
        super().setHelpText(help_text)
        self._notify_update()

    def setVisible(self, visible: bool = True):
        self._visible = bool(visible)
        self._notify_update()

    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)

    def render(self) -> str:
        html = ""
        
        # Label
        if self._label:
            label_html = format_label_with_shortcut(self._label)
            html += f'<label class="mana-selectionbox-label">{label_html}</label>'
        
        # List
        extra_attrs = {}
        if self._multi_selection:
            extra_attrs["multiple"] = True
        extra_attrs["size"] = "8"  # Default visible rows
        extra_attrs["title"] = self.helpText() or None
        if self.notifyContextMenu():
            extra_attrs["data-notify-context-menu"] = "1"
        
        attrs = widget_attrs(
            self.id(),
            "YSelectionBox",
            self._enabled,
            self._visible,
            extra_attrs=extra_attrs
        )
        
        options_html = ""
        for i, item in enumerate(self._items):
            selected = " selected" if item in self._selected_items else ""
            options_html += f'<option value="{i}"{selected}>{escape_html(item.label())}</option>'
        
        html += f'<select {attrs}>{options_html}</select>'
        
        return (f'<div data-container-for="{self.id()}" '
                f'class="mana-selectionbox-container">{html}</div>')
