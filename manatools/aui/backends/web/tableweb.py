"""Web backend Table implementation."""
from ...yui_common import (YSelectionWidget, YTableHeader, YTableItem,
                            YAlignmentType, YWidgetEvent, YEventReason)
from .commonweb import widget_attrs, escape_html, is_initial_render

class YTableWeb(YSelectionWidget):
    """Table view widget."""
    def __init__(self, parent=None, header: YTableHeader = None, multiSelection: bool = False):
        super().__init__(parent)
        self._header = header or YTableHeader()
        self._multi_selection = multiSelection
        self._rows = []
        self._changed_item = None

    def widgetClass(self):
        return "YTable"

    def addItem(self, item, notify=True):
        if isinstance(item, YTableItem):
            self._rows.append(item)
        if notify:
            self._notify_update()
        return item

    def addItems(self, items):
        for item in items:
            if isinstance(item, YTableItem):
                self._rows.append(item)
        self._notify_update()

    def rebuildTable(self):
        self._notify_update()

    def changedItem(self):
        """Return the last row that was changed (checkbox toggle or selection), or None."""
        return self._changed_item

    def _handle_selection_change(self, index: int, value: str = None):
        """Handle row selection from browser click (index = absolute position in _rows[])."""
        if 0 <= index < len(self._rows):
            row = self._rows[index]
            self._changed_item = row
            if not self._multi_selection:
                self._selected_items = [row]
            else:
                if row in self._selected_items:
                    self._selected_items.remove(row)
                else:
                    self._selected_items.append(row)

    def _handle_checkbox_change(self, row_index: int, col_index: int, checked: bool):
        """Handle a checkbox cell toggle from the browser.

        Mirrors Qt setData(CheckStateRole): updates the cell model, tracks
        _changed_item, and posts YWidgetEvent(ValueChanged) if notify() is set.
        """
        if not (0 <= row_index < len(self._rows)):
            return
        row = self._rows[row_index]
        try:
            cell = row.cell(col_index)
        except Exception:
            cell = None
        if cell is None:
            return
        cell.setChecked(checked)
        self._changed_item = row
        dlg = self.findDialog()
        if dlg is not None and self.notify():
            dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))

    def selectItem(self, item, selected=True):
        if selected:
            if item not in self._selected_items:
                self._selected_items.append(item)
        else:
            if item in self._selected_items:
                self._selected_items.remove(item)
        self._notify_update()

    def deleteAllItems(self):
        self._rows.clear()
        self._selected_items.clear()
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

    def _column_align_style(self, col: int) -> str:
        """Return an inline style attribute string for column alignment, or ''."""
        try:
            align = self._header.alignment(col)
        except Exception:
            return ""
        if align == YAlignmentType.YAlignCenter:
            return ' style="text-align:center"'
        if align == YAlignmentType.YAlignEnd:
            return ' style="text-align:right"'
        return ""

    def _render_rows_html(self) -> str:
        """Return the inner HTML of <tbody>: all <tr> rows, no wrapping tag.

        Called both from render() (full path) and by the dialog when pushing
        deferred row content via WebSocket after the browser connects.
        """
        rows = []
        for row_idx, row in enumerate(self._rows):
            sel_class = ' selected' if row in self._selected_items else ''
            cells = ''
            for i in range(row.cellCount()):
                cell = row.cell(i)
                align_style = self._column_align_style(i)
                if self._header.isCheckboxColumn(i):
                    checked_attr = ' checked' if (cell and cell.checked()) else ''
                    cells += (f'<td{align_style}>'
                              f'<input type="checkbox" class="form-check-input mana-table-checkbox"'
                              f' data-row="{row_idx}" data-col="{i}"{checked_attr}>'
                              f'</td>')
                else:
                    cells += f'<td{align_style}>{escape_html(cell.label()) if cell else ""}</td>'
            rows.append(f'<tr class="mana-table-row{sel_class}">{cells}</tr>')
        return ''.join(rows)

    def render(self) -> str:
        # Outer wrapper carries the widget identity (id, data-widget-class, visible).
        # enabled=True: <div> cannot carry the HTML disabled attribute; the enabled
        # state is propagated to the inner form controls manually below.
        attrs = widget_attrs(self.id(), "YTable", True, self._visible)
        disabled_attr = ' disabled' if not self._enabled else ''

        # Controls bar: search input only (page-size selector omitted by default)
        controls = (
            '<div class="mana-table-controls">'
            f'<input type="search" class="form-control form-control-sm mana-table-search"'
            f' placeholder="Search\u2026" aria-label="Search"{disabled_attr}>'
            '</div>'
        )

        # Inner <table> — Bootstrap styled; intentionally has no widget id
        thead = '<thead><tr>'
        for i in range(self._header.columns()):
            align_style = self._column_align_style(i)
            thead += f'<th scope="col"{align_style}>{escape_html(self._header.header(i))}</th>'
        thead += '</tr></thead>'

        # On the initial HTTP render, emit a loading skeleton so the browser
        # can paint the page quickly.  The real rows are pushed via WebSocket
        # as soon as the connection is established (see dialogweb._push_deferred_tables).
        if is_initial_render() and self._rows:
            col_count = max(self._header.columns(), 1)
            tbody = (
                f'<tbody>'
                f'<tr class="mana-table-loading">'
                f'<td colspan="{col_count}" class="text-center text-muted py-3">'
                f'<span class="spinner-border spinner-border-sm me-2" role="status">'
                f'</span>Loading\u2026'
                f'</td></tr>'
                f'</tbody>'
            )
        else:
            tbody = f'<tbody>{self._render_rows_html()}</tbody>'

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
