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
from functools import partial
import logging
from ...yui_common import *


class YTableWidgetItem(QtWidgets.QTableWidgetItem):
    """QTableWidgetItem subclass that prefers a stored sort key (UserRole)
    when comparing for sorting. Falls back to the default behaviour.
    """
    def __lt__(self, other):
        try:
            my_sort = self.data(QtCore.Qt.UserRole)
            other_sort = other.data(QtCore.Qt.UserRole)
            if my_sort is not None and other_sort is not None:
                return str(my_sort) < str(other_sort)
        except Exception:
            pass
        return super(YTableWidgetItem, self).__lt__(other)


class YTableQt(YSelectionWidget):
    def __init__(self, parent, header: YTableHeader, multiSelection=False):
        super().__init__(parent)
        self._header = header
        self._multi = bool(multiSelection)
        # force single-selection if any checkbox cells present
        if self._header is not None:
            try:
                for c_idx in range(self._header.columns()):
                    if self._header.isCheckboxColumn(c_idx):
                        self._multi = False
                        break
            except Exception:
                pass
        else:
            raise ValueError("YTableQt requires a YTableHeader")

        self._table = None
        self._row_to_item = {}
        self._item_to_row = {}
        self._suppress_selection_handler = False
        self._suppress_item_change = False
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        self._changed_item = None

    def widgetClass(self):
        return "YTable"

    def _header_is_checkbox(self, col):
        try:
            if getattr(self, '_header', None) is None:
                return False
            if hasattr(self._header, 'isCheckboxColumn'):
                return bool(self._header.isCheckboxColumn(col))
            return False
        except Exception:
            return False

    def _create_backend_widget(self):
        tbl = QtWidgets.QTableWidget()
        tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        mode = QtWidgets.QAbstractItemView.MultiSelection if self._multi else QtWidgets.QAbstractItemView.SingleSelection
        tbl.setSelectionMode(mode)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tbl.itemSelectionChanged.connect(self._on_selection_changed)
        #tbl.itemChanged.connect(self._on_item_changed)
        self._table = tbl
        self._backend_widget = tbl
        # respect initial enabled state
        try:
            self._table.setEnabled(bool(getattr(self, "_enabled", True)))
        except Exception:
            pass
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
        cols = 0
        any_checkbox = False
        if getattr(self, '_header', None) is not None and hasattr(self._header, 'columns'):
            try:
                cols = int(self._header.columns())
            except Exception:
                cols = 0
            # any_checkbox if header declares any checkbox column
            try:
                for c_idx in range(cols):
                    if self._header_is_checkbox(c_idx):
                        any_checkbox = True
                        break
            except Exception:
                any_checkbox = False
        if cols <= 0:
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

        # set column headers if available
        try:
            headers = []
            for c in range(cols):
                if getattr(self, '_header', None) is not None and hasattr(self._header, 'hasColumn') and self._header.hasColumn(c):
                    headers.append(self._header.header(c))
                else:
                    headers.append("")
            try:
                self._table.setColumnCount(cols)
                self._table.setHorizontalHeaderLabels(headers)
            except Exception:
                pass
        except Exception:
            pass

        # clear existing
        self._row_to_item.clear()
        self._item_to_row.clear()
        # clear contents only to preserve header labels
        self._table.clearContents()
        self._table.setRowCount(0)
        # ensure column count already set above

        # build rows (suppress item change notifications while programmatically populating)
        try:
            self._suppress_item_change = True
            for row_idx, it in enumerate(list(getattr(self, '_items', []) or [])):
                try:
                    self._table.insertRow(row_idx)
                    self._row_to_item[row_idx] = it
                    self._item_to_row[it] = row_idx
                    # populate cells: only up to 'cols' columns defined by header/detection
                    for col in range(cols):
                        cell = None
                        try:
                            cell = it.cell(col) if hasattr(it, 'cell') else None
                        except Exception:
                            cell = None

                        text = ""
                        sort_key = None
                        if cell is not None:
                            try:
                                text = cell.label()
                            except Exception:
                                text = ""
                            try:
                                if hasattr(cell, 'hasSortKey') and cell.hasSortKey():
                                    sort_key = cell.sortKey()
                            except Exception:
                                sort_key = None

                        # create item that supports sortKey via UserRole
                        qit = YTableWidgetItem(text)
                        if sort_key is not None:
                            try:
                                qit.setData(QtCore.Qt.UserRole, sort_key)
                            except Exception:
                                pass

                        # determine if this column is a checkbox column according to header
                        is_checkbox_col = False
                        try:
                            if getattr(self, '_header', None) is not None:
                                is_checkbox_col = self._header_is_checkbox(col)
                            else:
                                # fallback: treat as checkbox if cell explicitly has _checked
                                is_checkbox_col = (getattr(cell, '_checked', None) is not None)
                        except Exception:
                            is_checkbox_col = (getattr(cell, '_checked', None) is not None)

                        # apply flags and, for checkbox columns, prefer a centered checkbox widget
                        try:
                            flags = qit.flags() | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
                            if is_checkbox_col:
                                # keep item non-user-checkable; we'll install a centered QCheckBox widget
                                qit.setFlags(flags)
                                # set sortable value if no explicit sort key
                                if sort_key is None:
                                    try:
                                        qit.setData(QtCore.Qt.UserRole, 1 if (cell is not None and cell.checked()) else 0)
                                    except Exception:
                                        pass
                            else:
                                qit.setFlags(flags)
                        except Exception:
                            pass

                        # alignment according to header
                        try:
                            if getattr(self, '_header', None) is not None and hasattr(self._header, 'alignment') and self._header.hasColumn(col):
                                align = self._header.alignment(col)
                                if align == YAlignmentType.YAlignCenter:
                                    qit.setTextAlignment(QtCore.Qt.AlignCenter)
                                elif align == YAlignmentType.YAlignEnd:
                                    qit.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                                else:
                                    qit.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
                        except Exception:
                            pass

                        try:
                            self._table.setItem(row_idx, col, qit)
                            # for checkbox columns, install a checkbox widget honoring header alignment and connect
                            if is_checkbox_col:
                                try:
                                    chk = QtWidgets.QCheckBox()
                                    try:
                                        chk.setChecked(cell.checked() if cell is not None else False)
                                    except Exception:
                                        chk.setChecked(False)
                                    chk.setFocusPolicy(QtCore.Qt.NoFocus)
                                    container = QtWidgets.QWidget()
                                    lay = QtWidgets.QHBoxLayout(container)
                                    lay.setContentsMargins(0, 0, 0, 0)
                                    # determine alignment from header
                                    try:
                                        align_type = self._header.alignment(col)
                                    except Exception:
                                        align_type = YAlignmentType.YAlignBegin
                                    if align_type == YAlignmentType.YAlignCenter:
                                        lay.addStretch(1)
                                        lay.addWidget(chk, alignment=QtCore.Qt.AlignCenter)
                                        lay.addStretch(1)
                                    elif align_type == YAlignmentType.YAlignEnd:
                                        lay.addStretch(1)
                                        lay.addWidget(chk, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                                    else:
                                        lay.addWidget(chk, alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
                                        lay.addStretch(1)
                                    self._table.setCellWidget(row_idx, col, container)
                                    chk.toggled.connect(partial(self._on_checkbox_toggled, row_idx, col))
                                except Exception:
                                    pass
                        except Exception:
                            pass
                except Exception:
                    pass

        finally:
            self._suppress_item_change = False

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
        self._logger.debug("_on_selection_changed") 
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
                if self.notify():
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
        self._logger.debug("_on_item_changed: row=%d col=%d", qitem.row(), qitem.column())
        try:
            # Only treat as checkbox change if header declares this column as checkbox
            col = qitem.column()
            is_checkbox_col = False
            try:
                is_checkbox_col = self._header_is_checkbox(col)
            except Exception:
                is_checkbox_col = bool(qitem.flags() & QtCore.Qt.ItemIsUserCheckable)
            if not is_checkbox_col:
                return
            row = qitem.row()
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
                self._changed_item = it
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

    def _on_checkbox_toggled(self, row, col, checked):
        # update model and sort role when the embedded checkbox widget toggles
        self._logger.debug("_on_checkbox_toggled: row=%d col=%d checked=%s", row, col, checked)
        try:
            it = self._row_to_item.get(row, None)
            if it is None:
                return
            cell = it.cell(col)
            if cell is None:
                return
            try:
                cell.setChecked(bool(checked))
                self._changed_item = it
            except Exception:
                pass
            # keep sorting role consistent if no explicit sort key
            try:
                qit = self._table.item(row, col)
                if qit is not None and (cell is not None) and not (hasattr(cell, 'hasSortKey') and cell.hasSortKey()):
                    qit.setData(QtCore.Qt.UserRole, 1 if checked else 0)
            except Exception:
                pass
            # notify value change
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
        
        item.setIndex(len(self._items) - 1)
        if getattr(self, '_table', None) is not None:
            self.rebuildTable()

    def addItems(self, items):
        '''add multiple items to the table. This is more efficient than calling addItem repeatedly.'''
        for item in items:
            if isinstance(item, str):
                item = YTableItem(item)
                super().addItem(item)
            elif isinstance(item, YTableItem):
                super().addItem(item)
            else:
                self._logger.error("YTable.addItem: invalid item type %s", type(item))
                raise TypeError("YTable.addItem expects a YTableItem or string label")
            item.setIndex(len(self._items) - 1)
        if getattr(self, '_table', None) is not None:
            self.rebuildTable()

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
            self._changed_item = None
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
                # keep header labels intact
                self._table.clearContents()
        except Exception:
            pass

    def changedItem(self):
        return self._changed_item

    def _set_backend_enabled(self, enabled):
        """Enable/disable the Qt table at runtime."""
        try:
            if getattr(self, "_table", None) is not None:
                self._table.setEnabled(bool(enabled))
        except Exception:
            pass
