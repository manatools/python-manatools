# -*- coding: utf-8 -*-
"""
Web backend DumbTab implementation.

Author: Matteo Pasotti <xquiet@coriolite.com>

License: LGPLv2+

Renders a Bootstrap 5.3 nav-tabs bar with a single content area.
Tab switching is driven server-side: clicking a tab sends a
SelectionChanged event; the application (e.g. via YReplacePoint) is
responsible for updating the content area.
"""
from ...yui_common import YSelectionWidget, YItem, YWidgetEvent, YEventReason
from .commonweb import widget_attrs, escape_html


class YDumbTabWeb(YSelectionWidget):
    """Tab bar widget with Bootstrap 5.3 nav-tabs and a single content area."""

    def __init__(self, parent=None):
        super().__init__(parent)

    def widgetClass(self):
        return "YDumbTab"

    # ------------------------------------------------------------------
    # yui API
    # ------------------------------------------------------------------

    def setNotify(self, notify: bool = True):
        self._notify = bool(notify)

    def notify(self) -> bool:
        return getattr(self, '_notify', False)

    def addTab(self, label: str) -> YItem:
        """Convenience helper: create a YItem from a plain string and add it."""
        item = YItem(label)
        self.addItem(item)
        return item

    def addItem(self, item):
        """Add a tab item.  The first item added becomes the active tab."""
        super().addItem(item)
        if not self._selected_items:
            item.setSelected(True)
            self._selected_items = [item]

    def selectedItem(self):
        return self._selected_items[0] if self._selected_items else None

    def selectItem(self, item, selected: bool = True):
        """Programmatically activate *item* (single-selection semantics)."""
        if not selected or item not in self._items:
            return
        for it in self._items:
            it.setSelected(False)
        item.setSelected(True)
        self._selected_items = [item]
        self._notify_update()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _handle_selection_change(self, index: int, value=None):
        """Called by dialogweb when the browser reports a tab click."""
        if 0 <= index < len(self._items):
            self.selectItem(self._items[index])

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
        attrs = widget_attrs(self.id(), "YDumbTab", self._enabled, self._visible)
        selected = self.selectedItem()

        nav_items = ''
        for idx, item in enumerate(self._items):
            is_active = (item is selected)
            active_cls = ' active' if is_active else ''
            aria_sel = 'true' if is_active else 'false'
            nav_items += (
                f'<li class="nav-item" role="presentation">'
                f'<button class="nav-link mana-tab{active_cls}"'
                f' data-tab-index="{idx}"'
                f' type="button" role="tab"'
                f' aria-selected="{aria_sel}">'
                f'{escape_html(item.label())}'
                f'</button>'
                f'</li>'
            )

        nav = f'<ul class="nav nav-tabs mana-dumbtab-nav" role="tablist">{nav_items}</ul>'

        child_html = ''.join(child.render() for child in self._children)
        content = f'<div class="tab-content mana-dumbtab-content">{child_html}</div>'

        return f'<div {attrs}>{nav}{content}</div>'
