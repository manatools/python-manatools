# -*- coding: utf-8 -*-
"""
Web backend ComboBox implementation.

Author: Matteo Pasotti <xquiet@coriolite.com>

License: LGPLv2+

"""
from ...yui_common import YSelectionWidget, YItem
from .commonweb import widget_attrs, escape_html, format_label_with_shortcut


class YComboBoxWeb(YSelectionWidget):
    """Dropdown combo box widget."""

    def __init__(self, parent=None, label: str = "", editable: bool = False):
        super().__init__(parent)
        self._label = label
        self._editable = editable
        self._suppress_notify = False  # batch guard

    def widgetClass(self):
        return "YComboBox"

    def isEditable(self) -> bool:
        return self._editable

    def editable(self) -> bool:
        return self._editable

    def addItem(self, item, notify=True):
        """Add a single item and optionally push a UI update."""
        super().addItem(item)
        # Honor pre-selected state set by the caller before addItem().
        if hasattr(item, 'selected') and item.selected():
            if item not in self._selected_items:
                # ComboBox is single-selection: replace any existing selection.
                self._selected_items = [item]
        if notify and not self._suppress_notify:
            self._notify_update()
        return item

    def value(self) -> str:
        """Return the currently selected/entered value."""
        if self._selected_items:
            return self._selected_items[0].label()
        return ""

    def setValue(self, value: str):
        """Set the value (selects matching item or sets text if editable)."""
        for item in self._items:
            if item.label() == value:
                self._selected_items = [item]
                self._notify_update()
                return
        if self._editable:
            self._notify_update()

    def _handle_selection_change(self, index: int, value: str = None):
        """Handle selection change from browser.

        Prefers label-based lookup via ``value`` (the option's value attribute,
        which equals the item label) to avoid any index misalignment.  Falls
        back to positional lookup when ``value`` is None or unmatched.
        """
        if value is not None:
            for item in self._items:
                if item.label() == value:
                    self._selected_items = [item]
                    return
            # value sent but no match (should not happen with label-based options)
            # fall through to index-based lookup below

        if 0 <= index < len(self._items):
            self._selected_items = [self._items[index]]

    def updating(self):
        """Context manager: batch multiple mutations into a single broadcast.

        Usage::

            with combo.updating():
                combo.deleteAllItems()
                combo.setLabel("New label")
                combo.addItems(new_items)
            # one broadcast fires here
        """
        return _ComboUpdateContext(self)

    def setLabel(self, new_label: str):
        """Set the combo label and push a re-render to the browser."""
        super().setLabel(new_label)
        self._notify_update()

    def deleteAllItems(self):
        """Clear all items and push a re-render to the browser."""
        super().deleteAllItems()
        self._notify_update()

    def addItems(self, items):
        """Add items and push a re-render to the browser."""
        super().addItems(items)
        self._notify_update()

    def _set_backend_enabled(self, enabled: bool):
        self._notify_update()

    def setVisible(self, visible: bool = True):
        self._visible = bool(visible)
        self._notify_update()

    def _notify_update(self):
        if self._suppress_notify:
            return
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)

    def render(self) -> str:
        # The id goes on the outer container so that _schedule_update's
        # querySelector("#widget_N") + replaceWith() swaps the whole widget
        # (label + select) in one shot, preventing label duplication.
        # Use a neutral container class (not mana-ycombobox) to avoid
        # inheriting border/background CSS rules intended for the <select>.
        disabled_attr = ' disabled' if not self._enabled else ''
        hidden_style = ' style="display:none"' if not self._visible else ''

        inner = ""

        if self._label:
            # _label may contain &shortcut notation � escape first, then
            # format shortcuts so we never double-escape.
            label_html = format_label_with_shortcut(self._label)
            inner += f'<label class="mana-combobox-label">{label_html}</label>'

        options_html = ""
        for item in self._items:
            selected = " selected" if item in self._selected_items else ""
            # escape_html only once � used for both value attr and display text
            label = escape_html(item.label())
            options_html += f'<option value="{label}"{selected}>{label}</option>'

        inner += (
            f'<select'
            f' id="{self.id()}"'
            f' class="mana-ycombobox"'
            f' data-widget-class="YComboBox"'
            f' data-widget-id="{self.id()}"'
            f'{disabled_attr}>'
            f'{options_html}'
            f'</select>'
        )

        return (
            f'<div'
            f' data-container-for="{self.id()}"'
            f' class="mana-combobox-container"'
            f'{hidden_style}>'
            f'{inner}'
            f'</div>'
        )


class _ComboUpdateContext:
    """Context manager returned by YComboBoxWeb.updating()."""
    __slots__ = ("_widget",)

    def __init__(self, widget):
        self._widget = widget

    def __enter__(self):
        self._widget._suppress_notify = True
        return self._widget

    def __exit__(self, *_):
        self._widget._suppress_notify = False
        self._widget._notify_update()