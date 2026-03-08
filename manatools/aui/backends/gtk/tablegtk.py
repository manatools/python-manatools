# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
"""
GTK4 backend for YTable using GtkColumnView (virtual/lazy rendering).

Architecture
============
GtkListBox renders *all* rows eagerly: building 50 000 Gtk.CheckButton /
Gtk.Label widgets took 30 s+.  GtkColumnView uses SignalListItemFactory
callbacks and renders only the ~20-40 rows that fit in the viewport,
regardless of the total number of items.

Pipeline
--------
  YTableItem list
      |
      v
  Gio.ListStore[_RowObject]           -- data store,  O(1) append / O(N) splice
      |
      v
  Gtk.SortListModel                   -- sorting layer driven by header clicks
      |
      v
  Gtk.SingleSelection / MultiSelection -- selection model
      |
      v
  Gtk.ColumnView                      -- virtual view
       |
       +-- GtkColumnViewColumn x N    -- one per YTableHeader column
              |
              +-- GtkSignalListItemFactory  -- setup/bind/unbind/teardown
                   (called only for visible rows, O(visible x cols) total)

Complexity comparison
---------------------
                  GtkListBox (old)        GtkColumnView (new)
  rebuildTable()  O(N x cols) widgets     O(N) _RowObject alloc + splice()
  addItem()       O(N x cols)             O(1) store.append()
  addItems(N)     O(N x cols)             O(N) store.splice()
  scroll repaint  O(visible x cols)       O(visible x cols)  -- same

Sorting
-------
Clicking a column header toggles Ascending / Descending / None via
Gtk.ColumnViewSorter.  Sort key is cell.sortKey() if set, else cell.label().
Checkbox columns sort by checked state (False < True).

Preserved features
------------------
- Column headers from YTableHeader.header()
- Column alignment (Begin / Center / End) for header and cells
- Checkbox columns declared via YTableHeader.isCheckboxColumn()
- Selection driven by YTableItem.selected(); emits SelectionChanged
- Checkbox toggles emit ValueChanged and update YTableCell.checked()
- Single / multi selection modes
- Resizable columns via Gtk.ColumnViewColumn.set_resizable(True)
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, GLib, Gdk, GObject, Gio, Pango
import logging
from ...yui_common import *


# ---------------------------------------------------------------------------
# GObject wrapper so YTableItem can live in a Gio.ListStore
# ---------------------------------------------------------------------------

class _RowObject(GObject.Object):
    """
    Lightweight GObject wrapper around a YTableItem.

    Gio.ListStore requires GObject instances.  This wrapper adds no overhead
    beyond GObject reference-counting machinery.
    """
    __gtype_name__ = '_YTableRowObject'

    def __init__(self, item: YTableItem):
        super().__init__()
        self.item = item


class YTableGtk(YSelectionWidget):
    """
    GTK4 implementation of YTable backed by GtkColumnView.

    GtkColumnView is a *virtual* list widget: it creates GTK widgets only for
    the rows that are currently visible in the viewport.  Adding 50 000 rows
    is O(N) memory (one _RowObject wrapper per row) and O(visible x cols)
    rendering cost -- independent of total row count.

    Features
    --------
    - Virtual rendering: ~20-40 row widgets allocated regardless of total rows
    - Sortable columns via clickable column headers (Gtk.SortListModel)
    - Resizable columns via Gtk.ColumnViewColumn.set_resizable(True)
    - Checkbox column support with alignment
    - Single / multi selection
    - CSS theming
    """

    # CSS provider is registered once per process/display to avoid accumulation.
    _css_provider_installed: bool = False

    def __init__(self, parent=None, header: YTableHeader = None,
                 multiSelection: bool = False):
        super().__init__(parent)
        if header is None:
            raise ValueError("YTableGtk requires a YTableHeader")
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

        self._backend_widget = None   # outer Gtk.ScrolledWindow
        self._column_view = None      # Gtk.ColumnView
        self._store = None            # Gio.ListStore[_RowObject]
        self._sort_model = None       # Gtk.SortListModel
        self._selection_model = None  # Single / MultiSelection

        # item -> position in _store (before sorting)
        self._item_to_pos: dict = {}
        self._suppress_selection = False
        self._changed_item = None

        self._logger = logging.getLogger(
            f"manatools.aui.gtk.{self.__class__.__name__}"
        )

        # Stretched by default; callers can override via setStretchable().
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def widgetClass(self) -> str:
        return "YTable"

    def _header_is_checkbox(self, col: int) -> bool:
        """Return True when column *col* is declared as a checkbox column."""
        try:
            return bool(self._header.isCheckboxColumn(col))
        except Exception:
            return False

    def _col_align(self, col: int):
        """Return the YAlignmentType for *col* (defaults to YAlignBegin)."""
        try:
            return self._header.alignment(col)
        except Exception:
            return YAlignmentType.YAlignBegin

    @staticmethod
    def _gtk_halign(align_t) -> Gtk.Align:
        """Map YAlignmentType -> Gtk.Align."""
        if align_t == YAlignmentType.YAlignCenter:
            return Gtk.Align.CENTER
        if align_t == YAlignmentType.YAlignEnd:
            return Gtk.Align.END
        return Gtk.Align.START

    @staticmethod
    def _xalign(align_t) -> float:
        if align_t == YAlignmentType.YAlignCenter:
            return 0.5
        if align_t == YAlignmentType.YAlignEnd:
            return 1.0
        return 0.0

    # ------------------------------------------------------------------
    # CSS (registered once per display)
    # ------------------------------------------------------------------

    def _install_css(self):
        """Register the application CSS once per process."""
        if YTableGtk._css_provider_installed:
            return
        css_provider = Gtk.CssProvider()
        css = """
        columnview.y-table > listview > row:nth-child(even) {
            background-color: alpha(@theme_bg_color, 0.5);
        }
        columnview.y-table > listview > row:hover {
            background-color: alpha(@theme_selected_bg_color, 0.15);
        }
        columnview.y-table > listview > row:selected {
            background-color: @theme_selected_bg_color;
            color: @theme_selected_fg_color;
        }
        """
        try:
            try:
                css_provider.load_from_data(css, -1)
            except TypeError:
                css_provider.load_from_data(css.encode())
            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.add_provider_for_display(
                    display, css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
                YTableGtk._css_provider_installed = True
        except Exception as exc:
            self._logger.debug("CSS setup failed: %s", exc)

    # ------------------------------------------------------------------
    # Widget creation
    # ------------------------------------------------------------------

    def _create_backend_widget(self):
        """
        Build the GtkColumnView hierarchy.

        Structure
        ---------
        Gtk.ScrolledWindow
          +-- Gtk.ColumnView  (virtual, one column per YTableHeader column)
                model: Gtk.SingleSelection | Gtk.MultiSelection
                         +-- Gtk.SortListModel
                               +-- Gio.ListStore[_RowObject]
        """
        self._install_css()

        # Data store
        self._store = Gio.ListStore.new(_RowObject)

        # Sorting layer -- driven by ColumnView header clicks automatically.
        self._sort_model = Gtk.SortListModel.new(self._store, None)

        # Selection model
        if self._multi:
            self._selection_model = Gtk.MultiSelection.new(self._sort_model)
        else:
            self._selection_model = Gtk.SingleSelection.new(self._sort_model)
            try:
                self._selection_model.set_autoselect(False)
            except Exception:
                pass

        # ColumnView
        self._column_view = Gtk.ColumnView.new(self._selection_model)
        self._column_view.set_show_row_separators(True)
        self._column_view.set_show_column_separators(True)
        self._column_view.set_hexpand(True)
        self._column_view.set_vexpand(True)
        try:
            self._column_view.get_style_context().add_class("y-table")
        except Exception:
            pass

        # Wire the ColumnView's built-in sorter to SortListModel so that
        # clicking a header automatically sorts the model.
        try:
            self._sort_model.set_sorter(self._column_view.get_sorter())
        except Exception as exc:
            self._logger.debug("set_sorter failed: %s", exc)

        # Build one column per header entry.
        self._build_columns()

        # Selection-changed signal.
        try:
            self._selection_model.connect(
                "selection-changed", self._on_selection_changed
            )
        except Exception as exc:
            self._logger.debug("selection-changed connect failed: %s", exc)

        # ScrolledWindow wrapper.
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        try:
            sw.set_propagate_natural_height(True)
        except Exception:
            pass
        try:
            sw.set_child(self._column_view)
        except Exception:
            sw.add(self._column_view)

        sw.set_hexpand(self.stretchable(YUIDimension.YD_HORIZ))
        sw.set_vexpand(self.stretchable(YUIDimension.YD_VERT))

        self._backend_widget = sw

        self._apply_initial_state()
        self._logger.debug("_create_backend_widget: %s", self.debugLabel())

        # Populate if items were added before the widget was created.
        if getattr(self, '_items', None):
            self.rebuildTable()

    def _build_columns(self):
        """Create one GtkColumnViewColumn per header column."""
        try:
            n_cols = int(self._header.columns())
        except Exception:
            return

        for col in range(n_cols):
            is_cb = self._header_is_checkbox(col)
            try:
                title = self._header.header(col) or ""
            except Exception:
                title = ""

            factory = Gtk.SignalListItemFactory.new()
            factory.connect(
                "setup", lambda f, li, c=col: self._factory_setup(li, c)
            )
            factory.connect(
                "bind", lambda f, li, c=col: self._factory_bind(li, c)
            )
            factory.connect(
                "unbind", lambda f, li, c=col: self._factory_unbind(li, c)
            )
            factory.connect(
                "teardown", lambda f, li, c=col: self._factory_teardown(li, c)
            )

            column = Gtk.ColumnViewColumn.new(title, factory)
            column.set_resizable(True)
            # Checkbox columns are narrow; text columns expand to fill space.
            column.set_expand(not is_cb)

            # Attach a CustomSorter so the column is sortable.
            try:
                sorter = Gtk.CustomSorter.new(
                    self._make_sort_func(col), None
                )
                column.set_sorter(sorter)
            except Exception as exc:
                self._logger.debug("column %d sorter failed: %s", col, exc)

            self._column_view.append_column(column)

    def _make_sort_func(self, col: int):
        """Return a GtkCustomSorterFunc for column *col*."""
        is_cb = self._header_is_checkbox(col)

        def _sort(a: GObject.Object, b: GObject.Object, _user_data) -> int:
            def _key(obj):
                try:
                    cell = obj.item.cell(col)
                    if cell is None:
                        return ""
                    if is_cb:
                        return 0 if not cell.checked() else 1
                    if hasattr(cell, 'hasSortKey') and cell.hasSortKey():
                        return str(cell.sortKey())
                    return cell.label() or ""
                except Exception:
                    return ""

            ka, kb = _key(a), _key(b)
            if ka < kb:
                return -1
            if ka > kb:
                return 1
            return 0
        return _sort

    # ------------------------------------------------------------------
    # SignalListItemFactory callbacks  (called only for visible rows)
    # ------------------------------------------------------------------

    def _factory_setup(self, list_item: Gtk.ListItem, col: int):
        """
        Create the GTK widget for one cell slot.

        Called once when a row slot enters the visible area.  The widget is
        reused for different data via bind/unbind -- no allocation per row.
        """
        align_t = self._col_align(col)
        is_cb = self._header_is_checkbox(col)

        if is_cb:
            # CheckButton in an alignment wrapper.
            wrapper = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL, spacing=0
            )
            wrapper.set_hexpand(True)
            wrapper.set_halign(Gtk.Align.FILL)

            chk = Gtk.CheckButton()
            chk.set_valign(Gtk.Align.CENTER)

            def _spacer():
                s = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                s.set_hexpand(True)
                return s

            if align_t == YAlignmentType.YAlignCenter:
                wrapper.append(_spacer())
                wrapper.append(chk)
                wrapper.append(_spacer())
            elif align_t == YAlignmentType.YAlignEnd:
                wrapper.append(_spacer())
                chk.set_margin_end(6)
                wrapper.append(chk)
            else:
                chk.set_margin_start(6)
                wrapper.append(chk)
                wrapper.append(_spacer())

            # Stash direct reference so bind() can find the CheckButton.
            wrapper._chk = chk
            wrapper._chk_handler_id = None
            list_item.set_child(wrapper)
        else:
            lbl = Gtk.Label()
            lbl.set_halign(self._gtk_halign(align_t))
            lbl.set_xalign(self._xalign(align_t))
            lbl.set_margin_start(5)
            lbl.set_margin_end(5)
            lbl.set_hexpand(True)
            lbl.set_ellipsize(Pango.EllipsizeMode.END)
            list_item.set_child(lbl)

    def _factory_bind(self, list_item: Gtk.ListItem, col: int):
        """
        Populate the recycled widget with data from the current row.

        Called every time a row scrolls into view (or data changes).
        O(1) per cell -- no widget allocation.
        """
        row_obj = list_item.get_item()
        if row_obj is None:
            return
        item = row_obj.item
        child = list_item.get_child()
        if child is None:
            return

        if self._header_is_checkbox(col):
            chk = getattr(child, '_chk', None)
            if chk is None:
                return
            cell = None
            try:
                cell = item.cell(col)
            except Exception:
                pass
            checked = bool(cell.checked()) if cell is not None else False

            # Disconnect any previous handler before changing state.
            hid = getattr(child, '_chk_handler_id', None)
            if hid is not None:
                try:
                    chk.disconnect(hid)
                except Exception:
                    pass
                child._chk_handler_id = None

            chk.set_active(checked)

            def _on_toggled(btn, _item=item, _col=col):
                try:
                    c = _item.cell(_col)
                    if c is not None:
                        c.setChecked(bool(btn.get_active()))
                    self._changed_item = _item
                    dlg = self.findDialog()
                    if dlg is not None and self.notify():
                        dlg._post_event(
                            YWidgetEvent(self, YEventReason.ValueChanged)
                        )
                except Exception:
                    self._logger.exception("Checkbox toggle failed")

            child._chk_handler_id = chk.connect("toggled", _on_toggled)
        else:
            cell = None
            try:
                cell = item.cell(col)
            except Exception:
                pass
            txt = cell.label() if cell is not None else ""
            child.set_text(txt if txt is not None else "")

    def _factory_unbind(self, list_item: Gtk.ListItem, col: int):
        """
        Disconnect the toggled signal before the widget is recycled.

        Prevents stale item references from leaking into the recycled widget.
        """
        if not self._header_is_checkbox(col):
            return
        child = list_item.get_child()
        if child is None:
            return
        chk = getattr(child, '_chk', None)
        hid = getattr(child, '_chk_handler_id', None)
        if chk is not None and hid is not None:
            try:
                chk.disconnect(hid)
            except Exception:
                pass
            child._chk_handler_id = None

    def _factory_teardown(self, list_item: Gtk.ListItem, col: int):
        """Remove the child widget when the slot is permanently destroyed."""
        try:
            list_item.set_child(None)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Selection signal
    # ------------------------------------------------------------------

    def _on_selection_changed(self, sel_model, position: int, n_items: int):
        """Slot for SelectionModel::selection-changed."""
        if self._suppress_selection:
            return
        self._logger.debug("_on_selection_changed position=%d n=%d",
                           position, n_items)
        try:
            new_selected = []
            n = self._sort_model.get_n_items()
            for i in range(n):
                if sel_model.is_selected(i):
                    row_obj = self._sort_model.get_item(i)
                    if row_obj is not None:
                        new_selected.append(row_obj.item)

            if not self._multi and len(new_selected) > 1:
                new_selected = [new_selected[-1]]

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

            self._selected_items = new_selected

            try:
                if self.notify():
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(
                            YWidgetEvent(self, YEventReason.SelectionChanged)
                        )
            except Exception:
                pass
        except Exception as exc:
            self._logger.debug("_on_selection_changed: %s", exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rebuild_index(self):
        """Rebuild _item_to_pos from the current _store contents."""
        self._item_to_pos.clear()
        n = self._store.get_n_items()
        for i in range(n):
            obj = self._store.get_item(i)
            if obj is not None:
                self._item_to_pos[obj.item] = i

    def _apply_selection_from_model(self):
        """
        Apply YTableItem.selected() flags to the GtkSelectionModel.

        Called after rebuildTable() / addItems().  Positions are looked up in
        the sort model (which may reorder rows) rather than the raw store.
        """
        if self._selection_model is None:
            return
        self._suppress_selection = True
        try:
            self._selection_model.unselect_all()
            n = self._sort_model.get_n_items()
            selected_positions = []
            for i in range(n):
                obj = self._sort_model.get_item(i)
                if obj is not None:
                    try:
                        if obj.item.selected():
                            selected_positions.append(i)
                    except Exception:
                        pass

            if not self._multi and len(selected_positions) > 1:
                selected_positions = [selected_positions[0]]

            for pos in selected_positions:
                try:
                    self._selection_model.select_item(pos, False)
                except Exception:
                    pass

            self._selected_items = []
            for pos in selected_positions:
                obj = self._sort_model.get_item(pos)
                if obj is not None:
                    self._selected_items.append(obj.item)
        except Exception as exc:
            self._logger.debug("_apply_selection_from_model: %s", exc)
        finally:
            self._suppress_selection = False

    def _apply_initial_state(self):
        """Apply enabled, tooltip and visibility after widget creation."""
        try:
            if self._backend_widget is not None:
                self._backend_widget.set_sensitive(
                    bool(getattr(self, "_enabled", True))
                )
        except Exception:
            pass
        try:
            ht = getattr(self, "_help_text", None)
            if ht and self._backend_widget is not None:
                self._backend_widget.set_tooltip_text(ht)
        except Exception:
            pass
        try:
            if self._backend_widget is not None:
                self._backend_widget.set_visible(self.visible())
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API -- table content
    # ------------------------------------------------------------------

    def rebuildTable(self):
        """
        Synchronise the view with the current item list.

        O(N) to wrap items in _RowObject; one Gio.ListStore.splice() call
        replaces all existing objects atomically.  GtkColumnView repaints
        only the visible viewport.
        """
        self._logger.debug("rebuildTable: %d items",
                           len(self._items) if self._items else 0)
        if self._column_view is None:
            self._create_backend_widget()
            return  # _create_backend_widget calls rebuildTable recursively

        items = list(getattr(self, '_items', []) or [])
        self._suppress_selection = True
        try:
            new_objects = [_RowObject(it) for it in items]
            # splice(pos, n_remove, additions) replaces everything atomically.
            self._store.splice(0, self._store.get_n_items(), new_objects)
            self._rebuild_index()
        except Exception as exc:
            self._logger.debug("rebuildTable: splice failed: %s", exc)
        finally:
            self._suppress_selection = False

        self._apply_selection_from_model()
        self._logger.debug("rebuildTable: done")

    def addItem(self, item):
        """
        Add a single YTableItem.  O(1) via one store.append() call.
        """
        if isinstance(item, str):
            item = YTableItem(item)
        if not isinstance(item, YTableItem):
            raise TypeError("YTableGtk.addItem expects a YTableItem or str")
        super().addItem(item)
        item.setIndex(len(self._items) - 1)

        if self._store is None:
            return  # will be populated on first _create_backend_widget

        pos = self._store.get_n_items()
        self._item_to_pos[item] = pos
        self._store.append(_RowObject(item))

        # Apply pre-selection if item arrives pre-marked.
        if getattr(item, 'selected', lambda: False)():
            self._suppress_selection = True
            try:
                n = self._sort_model.get_n_items()
                for i in range(n):
                    obj = self._sort_model.get_item(i)
                    if obj is not None and obj.item is item:
                        if not self._multi:
                            self._selection_model.unselect_all()
                            for prev in list(self._selected_items):
                                try:
                                    prev.setSelected(False)
                                except Exception:
                                    pass
                            self._selected_items = []
                        self._selection_model.select_item(i, False)
                        item.setSelected(True)
                        if not self._multi:
                            self._selected_items = [item]
                        elif item not in self._selected_items:
                            self._selected_items.append(item)
                        break
            except Exception as exc:
                self._logger.debug("addItem: pre-selection failed: %s", exc)
            finally:
                self._suppress_selection = False

    def addItems(self, items):
        """
        Add multiple items in a single batch.

        O(N): wraps items in _RowObject then calls one store.splice() at the
        tail.  GtkColumnView receives a single items-changed notification and
        repaints the visible viewport only once.
        """
        items = list(items)
        if not items:
            return

        start_pos = len(getattr(self, '_items', []) or [])
        new_objs = []
        for item in items:
            if isinstance(item, str):
                item = YTableItem(item)
                super().addItem(item)
            elif isinstance(item, YTableItem):
                super().addItem(item)
            else:
                raise TypeError("YTableGtk.addItems expects YTableItem or str")
            item.setIndex(len(self._items) - 1)
            new_objs.append((item, _RowObject(item)))

        if self._store is None:
            return  # will be populated in _create_backend_widget

        self._store.splice(
            start_pos, 0,
            [obj for _, obj in new_objs]
        )
        for idx, (item, _) in enumerate(new_objs):
            self._item_to_pos[item] = start_pos + idx

        self._apply_selection_from_model()

    def selectItem(self, item, selected: bool = True):
        """Select or deselect *item* in both model and view."""
        try:
            item.setSelected(bool(selected))
        except Exception:
            pass

        if self._selection_model is None:
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

        # Find position in sort model.
        n = self._sort_model.get_n_items()
        pos = None
        for i in range(n):
            obj = self._sort_model.get_item(i)
            if obj is not None and obj.item is item:
                pos = i
                break
        if pos is None:
            return

        self._suppress_selection = True
        try:
            if selected:
                if not self._multi:
                    self._selection_model.unselect_all()
                    for prev in list(self._selected_items):
                        try:
                            prev.setSelected(False)
                        except Exception:
                            pass
                    self._selected_items = []
                self._selection_model.select_item(pos, False)
                item.setSelected(True)
                if not self._multi:
                    self._selected_items = [item]
                elif item not in self._selected_items:
                    self._selected_items.append(item)
            else:
                self._selection_model.unselect_item(pos)
                try:
                    self._selected_items.remove(item)
                except ValueError:
                    pass
        except Exception as exc:
            self._logger.debug("selectItem failed: %s", exc)
        finally:
            self._suppress_selection = False

    def deleteAllItems(self):
        """Clear all items from the table."""
        try:
            super().deleteAllItems()
        except Exception:
            self._items = []
        self._selected_items = []
        self._changed_item = None
        self._item_to_pos.clear()
        if self._store is not None:
            self._suppress_selection = True
            try:
                self._store.remove_all()
            except Exception as exc:
                self._logger.debug("deleteAllItems: remove_all failed: %s", exc)
            finally:
                self._suppress_selection = False

    def changedItem(self):
        """Return the most recently changed item (last checkbox toggle)."""
        return self._changed_item

    # ------------------------------------------------------------------
    # YWidget overrides
    # ------------------------------------------------------------------

    def _set_backend_enabled(self, enabled: bool):
        """Propagate enabled/disabled state."""
        try:
            if self._backend_widget is not None:
                self._backend_widget.set_sensitive(bool(enabled))
        except Exception:
            pass

    def setVisible(self, visible: bool = True):
        super().setVisible(visible)
        try:
            if self._backend_widget is not None:
                self._backend_widget.set_visible(bool(visible))
        except Exception:
            self._logger.exception("setVisible failed")

    def setHelpText(self, help_text: str):
        super().setHelpText(help_text)
        try:
            if self._backend_widget is not None:
                self._backend_widget.set_tooltip_text(help_text)
        except Exception:
            self._logger.exception("setHelpText failed")

