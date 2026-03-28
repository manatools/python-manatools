"""
Web backend SelectionBox implementation.
"""

from ...yui_common import YSelectionWidget
from .commonweb import widget_attrs, escape_html, format_label_with_shortcut


class YSelectionBoxWeb(YSelectionWidget):
    """List selection box widget."""
    
    def __init__(self, parent=None, label: str = "", multi_selection: bool = False):
        super().__init__(parent)
        self._label = label
        self._multi_selection = multi_selection
    
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

    def _handle_selection_change(self, indices):
        """Handle selection change from browser."""
        if isinstance(indices, int):
            indices = [indices]
        
        self._selected_items = []
        for idx in indices:
            if 0 <= idx < len(self._items):
                self._selected_items.append(self._items[idx])
    
    def _set_backend_enabled(self, enabled: bool):
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
        
        return f'<div class="mana-selectionbox-container">{html}</div>'
