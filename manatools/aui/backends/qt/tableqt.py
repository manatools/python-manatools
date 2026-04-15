# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
"""
Qt backend for YTable using QTableView + QAbstractTableModel.

Using QAbstractTableModel instead of QTableWidget gives virtual (on-demand)
data delivery: only the ~30-50 rows visible in the viewport are ever
rendered, regardless of the total number of items in the table.

Complexity comparison:
                  QTableWidget (old)       QTableView + model (new)
  rebuildTable()  O(N x cols)              O(N) for index, O(visible x cols) paint
  addItem()       O(N x cols)              O(1) - insertRows signal only
  addItems(N)     O(N x cols)              O(N) - single insertRows signal
  scroll repaint  O(visible x cols)        O(visible x cols)  - same

Checkbox columns are rendered natively via Qt.CheckStateRole /
Qt.ItemIsUserCheckable: no QCheckBox widget is created per cell.

Sorting is handled inside _YTableModel.sort(), triggered by a header click.
"""
from PySide6 import QtWidgets, QtCore, QtGui
import logging
from ...yui_common import *


class _YTableModel(QtCore.QAbstractTableModel):
    """
    QAbstractTableModel backed by a list of YTableItems.

    Data is fetched lazily: data() is called only for cells that are
    currently visible in the QTableView viewport.  Population of 50 000
    items takes O(N) for the index dict and O(visible x cols) for the initial
    paint — compared to O(N x cols) QTableWidgetItem allocations before.
    """

    def __init__(self, owner: 'YTableQt', parent=None):
        super().__init__(parent)
        # owner is the enclosing YTableQt; item list lives in owner._items.
        self._owner = owner

    # ------------------------------------------------------------------
    # QAbstractTableModel interface
    # ------------------------------------------------------------------

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        """Return the number of rows.  Always 0 for child items (tree guard)."""
        if parent.isValid():
            return 0
        return len(getattr(self._owner, '_items', []) or [])

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        """Return the number of columns as declared by YTableHeader."""
        if parent.isValid():
            return 0
        try:
            return int(self._owner._header.columns())
        except Exception:
            return 0

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole):
        """
        Return cell data for *role*.  Called by Qt only for visible cells.

        Roles handled:
          DisplayRole      – cell text (empty string for checkbox columns)
          CheckStateRole   – Checked / Unchecked for checkbox columns
          TextAlignmentRole – alignment from YTableHeader.alignment()
          UserRole         – sort key (cell.sortKey()) if available
        """
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        items = getattr(self._owner, '_items', []) or []
        if row < 0 or row >= len(items):
            return None

        it = items[row]
        cell = None
        try:
            cell = it.cell(col)
        except Exception:
            pass
        is_cb = self._owner._header_is_checkbox(col)

        if role == QtCore.Qt.DisplayRole:
            if is_cb:
                return None  # checkbox cells have no text label
            try:
                return cell.label() if cell is not None else ""
            except Exception:
                return ""

        if role == QtCore.Qt.CheckStateRole:
            if not is_cb:
                return None
            try:
                val = bool(cell.checked()) if cell is not None else False
                # Return plain int so the value survives the QVariant C++ round-trip
                # intact. Use .value because int(Qt.CheckState) fails on some PySide6
                # builds that use strict enums. Qt.Checked.value=2, Qt.Unchecked.value=0.
                return QtCore.Qt.Checked.value if val else QtCore.Qt.Unchecked.value
            except Exception:
                return QtCore.Qt.Unchecked.value

        if role == QtCore.Qt.TextAlignmentRole:
            try:
                align = self._owner._header.alignment(col)
                if align == YAlignmentType.YAlignCenter:
                    return QtCore.Qt.AlignCenter
                elif align == YAlignmentType.YAlignEnd:
                    return QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            except Exception:
                pass
            return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter

        if role == QtCore.Qt.UserRole:
            if cell is not None:
                try:
                    if hasattr(cell, 'hasSortKey') and cell.hasSortKey():
                        return cell.sortKey()
                except Exception:
                    pass
            return None

        return None

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation,
                   role: int = QtCore.Qt.DisplayRole):
        """Return horizontal column labels from YTableHeader."""
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            try:
                return self._owner._header.header(section)
            except Exception:
                pass
        return None

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        """
        Item flags.

        Checkbox columns receive ItemIsUserCheckable so the view renders a
        native check-box indicator and toggles state via setData() on click,
        without opening an editor widget.
        """
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
        f = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if self._owner._header_is_checkbox(index.column()):
            f |= QtCore.Qt.ItemIsUserCheckable
        return f

    def setData(self, index: QtCore.QModelIndex, value,
                role: int = QtCore.Qt.EditRole) -> bool:
        """
        Handle checkbox toggle (CheckStateRole).

        Called automatically by QAbstractItemView when the user clicks the
        check-box indicator of an ItemIsUserCheckable cell.  Updates the
        YTableCell model and fires a ValueChanged event.
        """
        if not index.isValid() or role != QtCore.Qt.CheckStateRole:
            return False
        row, col = index.row(), index.column()
        items = getattr(self._owner, '_items', []) or []
        if row < 0 or row >= len(items):
            return False
        it = items[row]
        cell = None
        try:
            cell = it.cell(col)
        except Exception:
            pass
        if cell is None:
            return False
        try:
            # value is Qt.CheckState (a PySide6 enum); compare directly rather
            # than via int() which fails in PySide6 6.x strict-enum mode.
            checked = (value == QtCore.Qt.Checked)
            cell.setChecked(checked)
            self._owner._changed_item = it
            self._owner._logger.debug(
                "setData CheckStateRole: row=%d col=%d checked=%s", row, col, checked
            )
            self.dataChanged.emit(index, index, [QtCore.Qt.CheckStateRole])
        except Exception as exc:
            self._owner._logger.debug("setData(CheckStateRole) failed: %s", exc)
            return False
        # Notify the application.
        try:
            dlg = self._owner.findDialog()
            if dlg is not None and self._owner.notify():
                dlg._post_event(YWidgetEvent(self._owner, YEventReason.ValueChanged))
        except Exception:
            pass
        return True

    # ------------------------------------------------------------------
    # Sorting support
    # ------------------------------------------------------------------

    def sort(self, column: int,
             order: QtCore.Qt.SortOrder = QtCore.Qt.AscendingOrder):
        """
        Sort items in-place by *column*.

        Triggered by a user click on a horizontal header section when
        setSortingEnabled(True) is set on the view.  O(N log N) but only
        called on explicit user interaction, not during populate.
        """
        self.layoutAboutToBeChanged.emit()
        try:
            items = list(getattr(self._owner, '_items', []) or [])

            def _key(it):
                cell = None
                try:
                    cell = it.cell(column)
                except Exception:
                    pass
                if cell is not None:
                    try:
                        if hasattr(cell, 'hasSortKey') and cell.hasSortKey():
                            return str(cell.sortKey())
                        return cell.label() or ""
                    except Exception:
                        pass
                return ""

            reverse = (order == QtCore.Qt.DescendingOrder)
            items.sort(key=_key, reverse=reverse)
            # Update owner's list in place and rebuild index map.
            self._owner._items[:] = items
            self._owner._item_to_row.clear()
            for i, it in enumerate(items):
                self._owner._item_to_row[it] = i
        except Exception as exc:
            self._owner._logger.debug("sort: failed col=%d: %s", column, exc)
        finally:
            self.layoutChanged.emit()


class _CheckBoxColumnDelegate(QtWidgets.QStyledItemDelegate):
    """
    Per-column delegate for checkbox columns.

    Solves two Qt6 issues that cannot be fixed at the model level alone:

    1. *Alignment* — QStyledItemDelegate always places the checkbox indicator
       in the decoration rectangle, which is pinned to the left edge regardless
       of TextAlignmentRole.  paint() positions the indicator according to the
       alignment declared in YTableHeader.

    2. *Toggle with NoEditTriggers* — In Qt6, QAbstractItemView suppresses
       the built-in ItemIsUserCheckable toggle when editTriggers == NoEditTriggers.
       editorEvent() fires *before* that check, so the toggle is handled here
       unconditionally, independent of the view's edit-trigger policy.
    """

    def __init__(self, owner: 'YTableQt', parent=None):
        super().__init__(parent)
        self._owner = owner

    def paint(self, painter: QtGui.QPainter,
              option: QtWidgets.QStyleOptionViewItem,
              index: QtCore.QModelIndex) -> None:
        """
        Draw the item background then the checkbox indicator at the column's
        declared alignment (Begin / Center / End).
        """
        painter.save()
        try:
            opt = QtWidgets.QStyleOptionViewItem(option)
            self.initStyleOption(opt, index)
            style = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()

            # Selection / hover / alternate-row background + focus border.
            style.drawPrimitive(
                QtWidgets.QStyle.PrimitiveElement.PE_PanelItemViewItem,
                opt, painter, opt.widget
            )

            # Checkbox indicator size from the current style.
            cb_w = style.pixelMetric(
                QtWidgets.QStyle.PixelMetric.PM_IndicatorWidth, opt, opt.widget
            )
            cb_h = style.pixelMetric(
                QtWidgets.QStyle.PixelMetric.PM_IndicatorHeight, opt, opt.widget
            )

            # Horizontal position from column alignment.
            try:
                align = self._owner._header.alignment(index.column())
            except Exception:
                align = YAlignmentType.YAlignBegin

            r = option.rect
            cy = r.top() + (r.height() - cb_h) // 2
            if align == YAlignmentType.YAlignCenter:
                cx = r.left() + (r.width() - cb_w) // 2
            elif align == YAlignmentType.YAlignEnd:
                cx = r.right() - cb_w - 4
            else:
                cx = r.left() + 4

            # Draw just the indicator glyph (no label area).
            ind_opt = QtWidgets.QStyleOptionButton()
            ind_opt.rect = QtCore.QRect(cx, cy, cb_w, cb_h)
            ind_opt.state = QtWidgets.QStyle.StateFlag.State_Enabled
            # Read cell state directly — avoids the QVariant C++ round-trip that
            # converts Qt.CheckState enums to plain ints, breaking == comparisons.
            is_checked = False
            try:
                items = getattr(self._owner, '_items', []) or []
                row = index.row()
                if 0 <= row < len(items):
                    cell = items[row].cell(index.column())
                    if cell is not None:
                        is_checked = bool(cell.checked())
            except Exception:
                pass
            if is_checked:
                ind_opt.state |= QtWidgets.QStyle.StateFlag.State_On
            else:
                ind_opt.state |= QtWidgets.QStyle.StateFlag.State_Off

            style.drawPrimitive(
                QtWidgets.QStyle.PrimitiveElement.PE_IndicatorCheckBox,
                ind_opt, painter, opt.widget
            )
        finally:
            painter.restore()

    def editorEvent(self, event: QtCore.QEvent,
                    model: QtCore.QAbstractItemModel,
                    option: QtWidgets.QStyleOptionViewItem,
                    index: QtCore.QModelIndex) -> bool:
        """
        Toggle the checkbox on left-button release.

        Called by QAbstractItemView before its own event-handling logic,
        so this fires regardless of the view's editTriggers setting.
        Returning True consumes the event and prevents Qt from running its
        own (possibly suppressed) toggle code a second time.
        """
        if event.type() != QtCore.QEvent.Type.MouseButtonRelease:
            return False
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return False
        flags = model.flags(index)
        if not (flags & QtCore.Qt.ItemFlag.ItemIsEnabled):
            return False
        if not (flags & QtCore.Qt.ItemFlag.ItemIsUserCheckable):
            return False
        # Read current checked state directly from the cell to avoid the
        # QVariant C++ round-trip that corrupts enum comparisons.
        new_checked = True
        try:
            items = getattr(self._owner, '_items', []) or []
            row = index.row()
            if 0 <= row < len(items):
                cell = items[row].cell(index.column())
                if cell is not None:
                    new_checked = not bool(cell.checked())  # toggle
        except Exception:
            pass
        new_state = QtCore.Qt.Checked if new_checked else QtCore.Qt.Unchecked
        return bool(model.setData(index, new_state, QtCore.Qt.CheckStateRole))


class YTableQt(YSelectionWidget):
    """
    Qt backend for YTable.

    Uses QTableView + _YTableModel (QAbstractTableModel).
    The model delivers data on demand so only visible cells are ever rendered.

    Operation complexities:
      rebuildTable()  O(N) index rebuild; O(visible×cols) repaint
      addItem()       O(1) via beginInsertRows/endInsertRows
      addItems(N)     O(N) index rebuild; single repaint
      selectItem()    O(1) via _item_to_row dict
    """

    def __init__(self, parent, header: YTableHeader, multiSelection=False):
        # All instance attributes must be set BEFORE super().__init__(parent).
        # YWidget.__init__ calls parent.addChild(self), which causes
        # YDumbTabQt.addChild → get_backend_widget() → _create_backend_widget()
        # while this constructor is still executing.  _create_backend_widget()
        # must find every attribute it reads already in place.
        if header is None:
            raise ValueError("YTableQt requires a YTableHeader")
        self._header = header
        self._multi = bool(multiSelection)
        # Force single-selection when any checkbox column is present.
        try:
            for c_idx in range(self._header.columns()):
                if self._header.isCheckboxColumn(c_idx):
                    self._multi = False
                    break
        except Exception:
            pass

        self._view = None    # QTableView
        self._model = None   # _YTableModel
        # Backward-compat alias: some code may reference self._table.
        self._table = None
        self._item_to_row: dict = {}
        self._suppress_selection_handler = False
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        self._changed_item = None

        super().__init__(parent)  # may trigger _create_backend_widget via addChild

    def widgetClass(self):
        return "YTable"

    def _header_is_checkbox(self, col: int) -> bool:
        """Return True when column *col* is declared as a checkbox column."""
        try:
            if getattr(self, '_header', None) is None:
                return False
            return bool(self._header.isCheckboxColumn(col))
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Widget creation
    # ------------------------------------------------------------------

    def _create_backend_widget(self):
        """
        Build the QTableView and attach a _YTableModel.

        Selection changes are forwarded via selectionModel().selectionChanged.
        Checkbox clicks call model.setData(CheckStateRole) directly.
        """
        model = _YTableModel(self)
        view = QtWidgets.QTableView()
        view.setModel(model)

        view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        mode = (QtWidgets.QAbstractItemView.MultiSelection
                if self._multi else QtWidgets.QAbstractItemView.SingleSelection)
        view.setSelectionMode(mode)

        # NoEditTriggers prevents text-editor popups; checkbox clicks still call
        # model.setData(CheckStateRole) because that path bypasses the editor system.
        view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        # Allow the user to sort by clicking a column header.
        view.setSortingEnabled(True)

        try:
            view.setAlternatingRowColors(True)
        except Exception:
            pass
        try:
            view.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass

        # Install per-column delegate on every checkbox column.
        # This handles both alignment (paint) and toggle (editorEvent).
        try:
            for col_idx in range(int(self._header.columns())):
                if self._header_is_checkbox(col_idx):
                    view.setItemDelegateForColumn(
                        col_idx, _CheckBoxColumnDelegate(self, view)
                    )
        except Exception as exc:
            self._logger.debug("_create_backend_widget: delegate setup failed: %s", exc)

        self._model = model
        self._view = view
        self._table = view          # backward-compat alias
        self._backend_widget = view

        # Wire up selection changes.
        try:
            view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        except Exception as exc:
            self._logger.debug("_create_backend_widget: selectionChanged connect failed: %s", exc)

        # Apply initial state.
        try:
            view.setEnabled(bool(getattr(self, "_enabled", True)))
        except Exception:
            pass
        try:
            if getattr(self, "_help_text", None):
                view.setToolTip(self._help_text)
        except Exception:
            pass
        try:
            view.setVisible(self.visible())
        except Exception:
            pass

        self._logger.debug("_create_backend_widget: view ready")

        # Populate index if items were added before the widget was created.
        try:
            self.rebuildTable()
        except Exception:
            self._logger.exception("rebuildTable failed during _create_backend_widget")

    # ------------------------------------------------------------------
    # Model / view synchronisation
    # ------------------------------------------------------------------

    def rebuildTable(self):
        """
        Synchronise the view with the current item list.

        O(N) to rebuild _item_to_row; O(1) from Qt's perspective because
        beginResetModel/endResetModel does not create any widgets — the view
        repaints only the visible viewport (O(visible×cols)).
        """
        self._logger.debug("rebuildTable: %d items",
                           len(self._items) if self._items else 0)
        if self._model is None:
            self._create_backend_widget()
            return  # _create_backend_widget calls rebuildTable recursively

        self._suppress_selection_handler = True
        try:
            self._model.beginResetModel()
            self._item_to_row.clear()
            for i, it in enumerate(list(getattr(self, '_items', []) or [])):
                self._item_to_row[it] = i
            self._model.endResetModel()
        except Exception as exc:
            self._logger.debug("rebuildTable: model reset failed: %s", exc)
            try:
                self._model.endResetModel()
            except Exception:
                pass
        finally:
            self._suppress_selection_handler = False

        self._apply_selection_from_model()

    def _apply_selection_from_model(self):
        """
        Apply YTableItem.selected() flags to the QTableView selection model.

        Called after rebuildTable() and addItems() to restore pre-selection.
        """
        if self._view is None:
            return
        sel_model = self._view.selectionModel()
        if sel_model is None:
            return
        self._suppress_selection_handler = True
        try:
            sel_model.clearSelection()
            new_selected = []
            items = list(getattr(self, '_items', []) or [])
            for it in items:
                try:
                    if it.selected():
                        row = self._item_to_row.get(it)
                        if row is not None:
                            idx = self._model.index(row, 0)
                            sel_model.select(
                                idx,
                                QtCore.QItemSelectionModel.Select
                                | QtCore.QItemSelectionModel.Rows,
                            )
                            new_selected.append(it)
                except Exception:
                    pass
            # Enforce single-selection: deselect surplus rows.
            if not self._multi and len(new_selected) > 1:
                for it in new_selected[1:]:
                    row = self._item_to_row.get(it)
                    if row is not None:
                        idx = self._model.index(row, 0)
                        sel_model.select(
                            idx,
                            QtCore.QItemSelectionModel.Deselect
                            | QtCore.QItemSelectionModel.Rows,
                        )
                new_selected = new_selected[:1]
            self._selected_items = new_selected
        except Exception as exc:
            self._logger.debug("_apply_selection_from_model failed: %s", exc)
        finally:
            self._suppress_selection_handler = False

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _on_selection_changed(self, selected: QtCore.QItemSelection,
                              deselected: QtCore.QItemSelection):
        """Slot for QItemSelectionModel.selectionChanged."""
        if self._suppress_selection_handler:
            return
        self._logger.debug("_on_selection_changed")
        try:
            sel_rows = self._view.selectionModel().selectedRows()
            items = getattr(self, '_items', []) or []
            new_selected = []
            for idx in sel_rows:
                row = idx.row()
                if 0 <= row < len(items):
                    new_selected.append(items[row])

            if not self._multi and len(new_selected) > 1:
                new_selected = [new_selected[-1]]

            # Update .selected() flags.
            try:
                for it in list(getattr(self, '_items', []) or []):
                    it.setSelected(False)
                for it in new_selected:
                    it.setSelected(True)
            except Exception:
                pass

            self._selected_items = new_selected

            try:
                if self.notify():
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
            except Exception:
                pass
        except Exception as exc:
            self._logger.debug("_on_selection_changed: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def addItem(self, item):
        """
        Add a single item.  O(1) from Qt's perspective.

        beginInsertRows/endInsertRows notifies the view to repaint one new
        row without touching any existing row.
        """
        if isinstance(item, str):
            item = YTableItem(item)
            super().addItem(item)
        elif isinstance(item, YTableItem):
            super().addItem(item)
        else:
            self._logger.error("YTable.addItem: invalid item type %s", type(item))
            raise TypeError("YTable.addItem expects a YTableItem or string label")

        row = len(self._items) - 1
        item.setIndex(row)
        self._item_to_row[item] = row

        if self._model is not None:
            try:
                self._model.beginInsertRows(QtCore.QModelIndex(), row, row)
                self._model.endInsertRows()
            except Exception as exc:
                self._logger.debug("addItem: beginInsertRows failed: %s", exc)
            # Apply pre-selection when item arrives pre-marked.
            try:
                if callable(getattr(item, 'selected', None)) and item.selected():
                    self._suppress_selection_handler = True
                    try:
                        sel_model = self._view.selectionModel()
                        if not self._multi:
                            sel_model.clearSelection()
                            for prev in self._selected_items:
                                try:
                                    prev.setSelected(False)
                                except Exception:
                                    pass
                            self._selected_items = []
                        idx = self._model.index(row, 0)
                        sel_model.select(
                            idx,
                            QtCore.QItemSelectionModel.Select
                            | QtCore.QItemSelectionModel.Rows,
                        )
                        item.setSelected(True)
                        if not self._multi:
                            self._selected_items = [item]
                        elif item not in self._selected_items:
                            self._selected_items.append(item)
                    except Exception as exc:
                        self._logger.debug("addItem: selection failed: %s", exc)
                    finally:
                        self._suppress_selection_handler = False
            except Exception:
                pass

    def addItems(self, items):
        """
        Add multiple items in a single batch.

        O(N) to build the index; a single beginInsertRows/endInsertRows
        call notifies the view once — only the visible viewport is repainted.
        """
        items = list(items)
        if not items:
            return
        start_row = len(getattr(self, '_items', []) or [])
        for item in items:
            if isinstance(item, str):
                item = YTableItem(item)
                super().addItem(item)
            elif isinstance(item, YTableItem):
                super().addItem(item)
            else:
                self._logger.error("YTable.addItems: invalid item type %s", type(item))
                raise TypeError("YTable.addItems expects YTableItem or str")
        end_row = len(self._items) - 1
        # Build index for newly added items.
        for i, it in enumerate(self._items[start_row:]):
            row = start_row + i
            it.setIndex(row)
            self._item_to_row[it] = row
        if self._model is not None and end_row >= start_row:
            try:
                self._model.beginInsertRows(QtCore.QModelIndex(), start_row, end_row)
                self._model.endInsertRows()
            except Exception as exc:
                self._logger.debug("addItems: beginInsertRows failed: %s", exc)
        self._apply_selection_from_model()

    def selectItem(self, item, selected=True):
        """Select or deselect *item* in both model and view."""
        try:
            item.setSelected(bool(selected))
        except Exception:
            pass

        if self._view is None:
            # Model-only update (widget not yet created).
            if selected:
                if item not in self._selected_items:
                    if not self._multi:
                        self._selected_items = [item]
                    else:
                        self._selected_items.append(item)
            else:
                try:
                    self._selected_items.remove(item)
                except ValueError:
                    pass
            return

        row = self._item_to_row.get(item)
        if row is None:
            return
        sel_model = self._view.selectionModel()
        self._suppress_selection_handler = True
        try:
            if selected:
                if not self._multi:
                    sel_model.clearSelection()
                    for prev in self._selected_items:
                        try:
                            prev.setSelected(False)
                        except Exception:
                            pass
                    self._selected_items = []
                idx = self._model.index(row, 0)
                sel_model.select(
                    idx,
                    QtCore.QItemSelectionModel.Select
                    | QtCore.QItemSelectionModel.Rows,
                )
                if not self._multi:
                    self._selected_items = [item]
                elif item not in self._selected_items:
                    self._selected_items.append(item)
            else:
                idx = self._model.index(row, 0)
                sel_model.select(
                    idx,
                    QtCore.QItemSelectionModel.Deselect
                    | QtCore.QItemSelectionModel.Rows,
                )
                try:
                    self._selected_items.remove(item)
                except ValueError:
                    pass
        except Exception as exc:
            self._logger.debug("selectItem failed: %s", exc)
        finally:
            self._suppress_selection_handler = False

    def deleteAllItems(self):
        """Clear all items from the table."""
        try:
            super().deleteAllItems()
            self._changed_item = None
        except Exception:
            self._items = []
            self._selected_items = []
        self._item_to_row.clear()
        if self._model is not None:
            self._suppress_selection_handler = True
            try:
                self._model.beginResetModel()
                self._model.endResetModel()
            except Exception as exc:
                self._logger.debug("deleteAllItems: model reset failed: %s", exc)
            finally:
                self._suppress_selection_handler = False

    def changedItem(self):
        """Return the most recently changed item (last checkbox toggle)."""
        return self._changed_item

    def _set_backend_enabled(self, enabled: bool):
        """Propagate enabled/disabled state to the QTableView."""
        try:
            if getattr(self, "_view", None) is not None:
                self._view.setEnabled(bool(enabled))
        except Exception:
            pass

    def setVisible(self, visible: bool = True):
        super().setVisible(visible)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.setVisible(bool(visible))
        except Exception:
            self._logger.exception("setVisible failed")

    def setHelpText(self, help_text: str):
        super().setHelpText(help_text)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.setToolTip(help_text)
        except Exception:
            self._logger.exception("setHelpText failed")

