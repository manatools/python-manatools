# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
"""
Qt backend for YTable using QTableWidget.

Supports multi-column rows via `YTableItem`/`YTableCell` from `yui_common`.
Cells that have a checkbox (their `checked` attribute is not None) are
rendered as checkboxes and the table forces single-selection mode in that
case (to keep curses/simple-mode compatibility).
"""
from PySide6 import QtWidgets, QtCore, QtGui
import logging
from ...yui_common import *


class YTableQt(YSelectionWidget):
    def __init__(self, parent=None, header=None, multiSelection=False):
        super().__init__(parent)
        self._header = header
        self._multi = bool(multiSelection)
        self._immediate = self.notify()
        self._table = None
        self._row_to_item = {}
        self._item_to_row = {}
        self._suppress_selection_handler = False
        self._suppress_item_change = False
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")

    def widgetClass(self):
        return "YTable"

    def _create_backend_widget(self):
        tbl = QtWidgets.QTableWidget()
        tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        mode = QtWidgets.QAbstractItemView.MultiSelection if self._multi else QtWidgets.QAbstractItemView.SingleSelection
        tbl.setSelectionMode(mode)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tbl.itemSelectionChanged.connect(self._on_selection_changed)
        tbl.itemChanged.connect(self._on_item_changed)
        self._table = tbl
        self._backend_widget = tbl
        # populate if items already present
        try:
            self.rebuildTable()
        except Exception:
            self._logger.exception("rebuildTable failed during _create_backend_widget")

    def _detect_columns_and_checkboxes(self):
        # compute max columns and whether any checkbox cells present
        max_cols = 0
        any_checkbox = False
        for it in list(getattr(self, "_items", []) or []):
            try:
                cnt = it.cellCount() if hasattr(it, 'cellCount') else 0
                max_cols = max(max_cols, cnt)
                for c in it.cellsBegin() if hasattr(it, 'cellsBegin') else []:
                    try:
                        if getattr(c, '_checked', None) is not None:
                            any_checkbox = True
                            break
                    except Exception:
                        pass
            except Exception:
                pass
        return max_cols, any_checkbox

    def rebuildTable(self):
        self._logger.debug("rebuildTable: rebuilding table with %d items", len(self._items) if self._items else 0)
        if self._table is None:
            self._create_backend_widget()
        # determine columns and checkbox usage
        cols, any_checkbox = self._detect_columns_and_checkboxes()
        if cols <= 0:
            cols = 1
        # enforce single-selection if checkbox columns used
        if any_checkbox:
            self._multi = False
        mode = QtWidgets.QAbstractItemView.MultiSelection if self._multi else QtWidgets.QAbstractItemView.SingleSelection
        try:
            self._table.setSelectionMode(mode)
        except Exception:
            pass

        # clear existing
        self._row_to_item.clear()
        self._item_to_row.clear()
        self._table.clear()
        self._table.setRowCount(0)
        self._table.setColumnCount(cols)

        # build rows
        for row_idx, it in enumerate(list(getattr(self, '_items', []) or [])):
            try:
                self._table.insertRow(row_idx)
                self._row_to_item[row_idx] = it
                self._item_to_row[it] = row_idx
                # populate cells
                for col in range(cols):
                    cell = it.cell(col) if hasattr(it, 'cell') else None
                    if cell is None:
                        qit = QtWidgets.QTableWidgetItem("")
                    else:
                        text = cell.label()
                        qit = QtWidgets.QTableWidgetItem(text)
                        if getattr(cell, '_checked', None) is not None:
                            # checkbox column
                            qit.setFlags(qit.flags() | QtCore.Qt.ItemIsUserCheckable)
                            qit.setCheckState(QtCore.Qt.Checked if cell.checked() else QtCore.Qt.Unchecked)
                    try:
                        self._table.setItem(row_idx, col, qit)
                    except Exception:
                        pass
            except Exception:
                pass

        # apply selection from YTableItem.selected flags
        desired_rows = []
        try:
            for it, row in list(self._item_to_row.items()):
                try:
                    sel = False
                    if hasattr(it, 'selected') and callable(getattr(it, 'selected')):
                        sel = it.selected()
                    else:
                        sel = bool(getattr(it, '_selected', False))
                    if sel:
                        desired_rows.append(row)
                except Exception:
                    pass
        except Exception:
            pass

        # set selection programmatically
        try:
            self._suppress_selection_handler = True
            try:
                self._table.clearSelection()
            except Exception:
                pass
            if desired_rows:
                if self._multi:
                    for r in desired_rows:
                        try:
                            self._table.selectRow(r)
                        except Exception:
                            pass
                else:
                    # pick first desired row
                    try:
                        self._table.selectRow(desired_rows[0])
                    except Exception:
                        pass
            # update internal selected list
            new_selected = []
            for r in desired_rows:
                it = self._row_to_item.get(r, None)
                if it is not None:
                    try:
                        it.setSelected(True)
                    except Exception:
                        pass
                    new_selected.append(it)
            self._selected_items = new_selected
        finally:
            self._suppress_selection_handler = False

    def _on_selection_changed(self):
        if self._suppress_selection_handler:
            return
        try:
            sel_ranges = self._table.selectionModel().selectedRows()
            new_selected = []
            for idx in sel_ranges:
                try:
                    row = idx.row()
                    it = self._row_to_item.get(row, None)
                    if it is not None:
                        new_selected.append(it)
                except Exception:
                    pass

            # clear all selected flags then set for new_selected
            try:
                for it in list(getattr(self, '_items', []) or []):
                    try:
                        it.setSelected(False)
                    except Exception:
                        pass
                for it in new_selected:
                    try:
                        it.setSelected(True)
                    except Exception:
                        pass
            except Exception:
                pass

            # enforce single-selection semantics
            if not self._multi and len(new_selected) > 1:
                new_selected = [new_selected[-1]]

            self._selected_items = new_selected

            # notify immediate mode
            try:
                if self._immediate and self.notify():
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
            except Exception:
                pass
        except Exception:
            pass

    def _on_item_changed(self, qitem: QtWidgets.QTableWidgetItem):
        # handle checkbox toggles
        if self._suppress_item_change:
            return
        try:
            if not (qitem.flags() & QtCore.Qt.ItemIsUserCheckable):
                return
            row = qitem.row()
            col = qitem.column()
            it = self._row_to_item.get(row, None)
            if it is None:
                return
            cell = it.cell(col)
            if cell is None:
                return
            # update model checkbox
            try:
                checked = (qitem.checkState() == QtCore.Qt.Checked)
                cell.setChecked(checked)
            except Exception:
                pass
            # when checkbox is used, assume this is a value change
            try:
                dlg = self.findDialog()
                if dlg is not None and self.notify():
                    dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
            except Exception:
                pass
        except Exception:
            pass

    def addItem(self, item):
        if isinstance(item, str):
            item = YTableItem(item)
            super().addItem(item)
        elif isinstance(item, YTableItem):
            super().addItem(item)
        else:
            self._logger.error("YTable.addItem: invalid item type %s", type(item))
            raise TypeError("YTable.addItem expects a YTableItem or string label")
        try:
            item.setIndex(len(self._items) - 1)
        except Exception:
            pass
        try:
            if getattr(self, '_table', None) is not None:
                self.rebuildTable()
        except Exception:
            pass

    def addItems(self, items):
        for it in items:
            self.addItem(it)

    def selectItem(self, item, selected=True):
        # update model and view
        try:
            try:
                item.setSelected(bool(selected))
            except Exception:
                pass
            if getattr(self, '_table', None) is None:
                # just update model
                if selected:
                    if item not in self._selected_items:
                        if not self._multi:
                            self._selected_items = [item]
                        else:
                            self._selected_items.append(item)
                else:
                    try:
                        if item in self._selected_items:
                            self._selected_items.remove(item)
                    except Exception:
                        pass
                return

            row = self._item_to_row.get(item, None)
            if row is None:
                try:
                    self.rebuildTable()
                    row = self._item_to_row.get(item, None)
                except Exception:
                    row = None
            if row is None:
                return

            try:
                self._suppress_selection_handler = True
                if not self._multi and selected:
                    try:
                        self._table.clearSelection()
                    except Exception:
                        pass
                if selected:
                    self._table.selectRow(row)
                else:
                    try:
                        # deselect programmatically
                        sel_model = self._table.selectionModel()
                        idx = sel_model.model().index(row, 0)
                        sel_model.select(idx, QtCore.QItemSelectionModel.Deselect | QtCore.QItemSelectionModel.Rows)
                    except Exception:
                        pass
            finally:
                self._suppress_selection_handler = False

            # update internal list
            try:
                new_selected = []
                for idx in self._table.selectionModel().selectedRows():
                    it2 = self._row_to_item.get(idx.row(), None)
                    if it2 is not None:
                        new_selected.append(it2)
                if not self._multi and len(new_selected) > 1:
                    new_selected = [new_selected[-1]]
                self._selected_items = new_selected
            except Exception:
                pass
        except Exception:
            pass

    def deleteAllItems(self):
        try:
            super().deleteAllItems()
        except Exception:
            self._items = []
            self._selected_items = []
        try:
            self._row_to_item.clear()
        except Exception:
            pass
        try:
            self._item_to_row.clear()
        except Exception:
            pass
        try:
            if getattr(self, '_table', None) is not None:
                self._table.setRowCount(0)
                self._table.clear()
        except Exception:
            pass
