"""Web backend Table implementation."""
from ...yui_common import YSelectionWidget, YTableHeader, YTableItem
from .commonweb import widget_attrs, escape_html

class YTableWeb(YSelectionWidget):
    """Table view widget."""
    def __init__(self, parent=None, header: YTableHeader = None, multiSelection: bool = False):
        super().__init__(parent)
        self._header = header or YTableHeader()
        self._multi_selection = multiSelection
        self._rows = []

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
        """Return the last row that was selected/changed, or None."""
        return self._selected_items[-1] if self._selected_items else None

    def _handle_selection_change(self, index: int, value: str = None):
        """Handle row selection from browser click (index = absolute position in _rows[])."""
        if 0 <= index < len(self._rows):
            row = self._rows[index]
            if not self._multi_selection:
                self._selected_items = [row]
            else:
                if row in self._selected_items:
                    self._selected_items.remove(row)
                else:
                    self._selected_items.append(row)

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

    def render(self) -> str:
        # Outer wrapper carries the widget identity (id, data-widget-class, visible).
        # enabled=True: <div> cannot carry the HTML disabled attribute; the enabled
        # state is propagated to the inner form controls manually below.
        attrs = widget_attrs(self.id(), "YTable", True, self._visible)
        disabled_attr = ' disabled' if not self._enabled else ''

        # Controls bar: "Show N entries" selector + search input
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

        # Inner <table> — Bootstrap styled; intentionally has no widget id
        thead = '<thead><tr>'
        for i in range(self._header.columns()):
            thead += f'<th scope="col">{escape_html(self._header.header(i))}</th>'
        thead += '</tr></thead>'

        tbody = '<tbody>'
        for row in self._rows:
            sel_class = ' selected' if row in self._selected_items else ''
            tbody += f'<tr class="mana-table-row{sel_class}">'
            for i in range(row.cellCount()):
                cell = row.cell(i)
                tbody += f'<td>{escape_html(cell.label()) if cell else ""}</td>'
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
