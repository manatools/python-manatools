# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
"""
GTK backend for YTable using Gtk4.

Renders a header row via Gtk.Grid and rows via Gtk.ListBox. Supports:
- Column headers from `YTableHeader.header()`
- Column alignment from `YTableHeader.alignment()`
- Checkbox columns declared via `YTableHeader.isCheckboxColumn()`
- Selection driven by `YTableItem.selected()`; emits SelectionChanged on change
- Checkbox toggles emit ValueChanged and update `YTableCell.checked()`

Sorting UI is not implemented; if needed we can add clickable headers.
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
import logging
from ...yui_common import *


class YTableGtk(YSelectionWidget):
    def __init__(self, parent=None, header: YTableHeader = None, multiSelection=False):
        super().__init__(parent)
        if header is None:
            raise ValueError("YTableGtk requires a YTableHeader")
        self._header = header
        self._multi = bool(multiSelection)
        # force single-selection if any checkbox columns present
        try:
            for c_idx in range(self._header.columns()):
                if self._header.isCheckboxColumn(c_idx):
                    self._multi = False
                    break
        except Exception:
            pass
        self._backend_widget = None
        self._header_grid = None
        self._listbox = None
        self._row_to_item = {}
        self._item_to_row = {}
        self._rows = []
        self._suppress_selection_handler = False
        self._suppress_item_change = False
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        self._old_selected_items = []  # for change detection
        self._changed_item = None

    def widgetClass(self):
        return "YTable"

    def _create_backend_widget(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # Header grid
        header_grid = Gtk.Grid(column_spacing=12, row_spacing=0)
        try:
            cols = self._header.columns()
        except Exception:
            cols = 0
        for col in range(cols):
            try:
                txt = self._header.header(col)
            except Exception:
                txt = ""
            lbl = Gtk.Label(label=txt)
            try:
                align = self._header.alignment(col)
                if align == YAlignmentType.YAlignCenter:
                    lbl.set_xalign(0.5)
                elif align == YAlignmentType.YAlignEnd:
                    lbl.set_xalign(1.0)
                else:
                    lbl.set_xalign(0.0)
            except Exception:
                pass
            header_grid.attach(lbl, col, 0, 1, 1)

        # ListBox inside ScrolledWindow
        listbox = Gtk.ListBox()
        try:
            mode = Gtk.SelectionMode.MULTIPLE if self._multi else Gtk.SelectionMode.SINGLE
            listbox.set_selection_mode(mode)
        except Exception:
            pass

        sw = Gtk.ScrolledWindow()
        try:
            sw.set_child(listbox)
        except Exception:
            try:
                sw.add(listbox)
            except Exception:
                pass

        # Make expand according to parent stretching
        try:
            vbox.set_hexpand(self.stretchable(YUIDimension.YD_HORIZ))
            vbox.set_vexpand(self.stretchable(YUIDimension.YD_VERT))
            vbox.set_valign(Gtk.Align.FILL)
            listbox.set_hexpand(True)
            listbox.set_vexpand(True)
            listbox.set_valign(Gtk.Align.FILL)
            sw.set_hexpand(True)
            sw.set_vexpand(True)
            sw.set_valign(Gtk.Align.FILL)
        except Exception:
            pass

        self._backend_widget = vbox
        self._header_grid = header_grid
        self._listbox = listbox

        try:
            vbox.append(header_grid)
            vbox.append(sw)
        except Exception:
            try:
                vbox.add(header_grid)
                vbox.add(sw)
            except Exception:
                pass

        # respect initial enabled state
        try:
            if hasattr(self._backend_widget, "set_sensitive"):
                self._backend_widget.set_sensitive(bool(getattr(self, "_enabled", True)))
            if hasattr(self._listbox, "set_sensitive"):
                self._listbox.set_sensitive(bool(getattr(self, "_enabled", True)))
        except Exception:
            pass

        # connect selection handlers
        if self._multi:
            try:
                self._listbox.connect("selected-rows-changed", lambda lb: self._on_selected_rows_changed(lb))                    
                self._listbox.connect("row-activated", lambda lb, row: self._on_row_selected_for_multi(lb, row))
            except Exception:                   
                pass
        else:
            try:
                self._listbox.connect("row-selected", lambda lb, row: self._on_row_selected(lb, row))
            except Exception:
                pass

        self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())

        # populate if items exist
        try:
            if getattr(self, "_items", None):
                self.rebuildTable()
        except Exception:
            self._logger.exception("rebuildTable failed during _create_backend_widget")

    def _header_is_checkbox(self, col):
        try:
            return bool(self._header.isCheckboxColumn(col))
        except Exception:
            return False

    def rebuildTable(self):
        self._logger.debug("rebuildTable: %d items", len(self._items) if self._items else 0)
        if self._backend_widget is None or self._listbox is None:
            self._create_backend_widget()

        # clear rows
        try:
            self._row_to_item.clear()
            self._item_to_row.clear()
        except Exception:
            pass
        try:
            for row in list(self._rows):
                try:
                    self._listbox.remove(row)
                except Exception:
                    pass
            self._rows = []
        except Exception:
            pass

        # build rows
        try:
            cols = self._header.columns()
        except Exception:
            cols = 0
        if cols <= 0:
            cols = 1

        for row_idx, it in enumerate(list(getattr(self, '_items', []) or [])):
            try:
                row = Gtk.ListBoxRow()
                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

                for col in range(cols):
                    cell = it.cell(col) if hasattr(it, 'cell') else None
                    is_cb = self._header_is_checkbox(col)
                    # alignment for this column
                    try:
                        align_t = self._header.alignment(col)
                    except Exception:
                        align_t = YAlignmentType.YAlignBegin

                    if is_cb:
                        # render a checkbox honoring alignment
                        try:
                            chk = Gtk.CheckButton()
                            try:
                                chk.set_active(cell.checked() if cell is not None else False)
                            except Exception:
                                chk.set_active(False)
                            # place inside a box to honor alignment
                            cell_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                            if align_t == YAlignmentType.YAlignCenter:
                                cell_box.set_halign(Gtk.Align.CENTER)
                            elif align_t == YAlignmentType.YAlignEnd:
                                cell_box.set_halign(Gtk.Align.END)
                            else:
                                cell_box.set_halign(Gtk.Align.START)
                            cell_box.append(chk)
                            hbox.append(cell_box)
                            # connect toggle
                            def _on_toggled(btn, item=it, cindex=col):
                                try:
                                    c = item.cell(cindex)
                                    if c is not None:
                                        c.setChecked(bool(btn.get_active()))
                                    # track changed item
                                    self._changed_item = item
                                    # emit value changed
                                    dlg = self.findDialog()
                                    if dlg is not None and self.notify():
                                        dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
                                except Exception:
                                    pass
                            chk.connect("toggled", _on_toggled)
                        except Exception:
                            hbox.append(Gtk.Label(label=""))
                    else:
                        # render text label honoring alignment
                        txt = ""
                        try:
                            txt = cell.label() if cell is not None else ""
                        except Exception:
                            txt = ""
                        lbl = Gtk.Label(label=txt)
                        try:
                            if align_t == YAlignmentType.YAlignCenter:
                                lbl.set_xalign(0.5)
                            elif align_t == YAlignmentType.YAlignEnd:
                                lbl.set_xalign(1.0)
                            else:
                                lbl.set_xalign(0.0)
                        except Exception:
                            pass
                        hbox.append(lbl)

                row.set_child(hbox)
                self._listbox.append(row)
                self._row_to_item[row] = it
                self._item_to_row[it] = row
                self._rows.append(row)
            except Exception:
                pass

        # apply selection from model
        try:
            self._suppress_selection_handler = True
            if not self._multi:
                # single: select the first selected item
                for it in list(getattr(self, '_items', []) or []):
                    if hasattr(it, 'selected') and it.selected():
                        try:
                            row = self._item_to_row.get(it)
                            if row is not None:
                                self._listbox.select_row(row)
                            break
                        except Exception:
                            pass
            else:
                # multi: select all selected items
                for it in list(getattr(self, '_items', []) or []):
                    if hasattr(it, 'selected') and it.selected():
                        try:
                            row = self._item_to_row.get(it)
                            if row is not None:
                                self._listbox.select_row(row)
                        except Exception:
                            pass
        finally:
            self._suppress_selection_handler = False

    # selection handlers
    def _on_row_selected(self, listbox, row):
        if self._suppress_selection_handler:
            return
        try:
            # update selected flags
            for it in list(getattr(self, '_items', []) or []):
                try:
                    it.setSelected(False)
                except Exception:
                    pass
            if row is not None:
                it = self._row_to_item.get(row)
                if it is not None:
                    try:
                        it.setSelected(True)
                    except Exception:
                        pass
                    self._selected_items = [it]
            else:
                self._selected_items = []
            # notify
            try:
                if self.notify():
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
            except Exception:
                pass
        except Exception:
            pass

    def _on_selected_rows_changed(self, listbox):
        if self._suppress_selection_handler:
            return
        try:
            selected_rows = listbox.get_selected_rows() or []
            new_selected = []
            for row in selected_rows:
                it = self._row_to_item.get(row)
                if it is not None:
                    new_selected.append(it)
            # set flags
            try:
                for it in list(getattr(self, '_items', []) or []):
                    it.setSelected(False)
                for it in new_selected:
                    it.setSelected(True)
            except Exception:
                pass
            # clamp single-selection just in case
            if not self._multi and len(new_selected) > 1:
                new_selected = [new_selected[-1]]
            
            self._old_selected_items = self._selected_items
            self._selected_items = new_selected
            # notify
            try:
                if self.notify():
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
            except Exception:
                pass
        except Exception:
            pass

    def _on_row_selected_for_multi(self, listbox, row):
        """
        Handler for row selection in multi-selection mode: for de-selection.
        """
        if self._suppress_selection_handler:
            return
        self._logger.debug("_on_row_selected_for_multi called")
        sel_rows = listbox.get_selected_rows()
        it = self._row_to_item.get(row, None)
        if it is not None:
            if it in self._old_selected_items:
                self._listbox.unselect_row( row )
                it.setSelected( False )
                self._on_selected_rows_changed(listbox)
            else:
                self._old_selected_items = self._selected_items

    # API
    def addItem(self, item):
        if isinstance(item, str):
            item = YTableItem(item)
        if not isinstance(item, YTableItem):
            raise TypeError("YTableGtk.addItem expects a YTableItem or string label")
        super().addItem(item)
        try:
            item.setIndex(len(self._items) - 1)
        except Exception:
            pass
        try:
            if getattr(self, '_listbox', None) is not None:
                self.rebuildTable()
        except Exception:
            pass

    def addItems(self, items):
        for it in items:
            self.addItem(it)

    def selectItem(self, item, selected=True):
        try:
            item.setSelected(bool(selected))
        except Exception:
            pass
        if getattr(self, '_listbox', None) is None:
            # only update model
            if selected:
                if item not in self._selected_items:
                    self._selected_items.append(item)
            else:
                try:
                    if item in self._selected_items:
                        self._selected_items.remove(item)
                except Exception:
                    pass
            return
        try:
            row = self._item_to_row.get(item)
            if row is None:
                self.rebuildTable()
                row = self._item_to_row.get(item)
            if row is None:
                return
            self._suppress_selection_handler = True
            if selected:
                if not self._multi:
                    try:
                        # GTK4 ListBox does not have clearSelection; manually unselect others
                        for r in list(self._listbox.get_selected_rows() or []):
                            self._listbox.unselect_row(r)
                    except Exception:
                        pass
                self._listbox.select_row(row)
            else:
                try:
                    self._listbox.unselect_row(row)
                except Exception:
                    pass
        finally:
            self._suppress_selection_handler = False

    def deleteAllItems(self):
        try:
            super().deleteAllItems()
        except Exception:
            self._items = []
            self._selected_items = []
            self._changed_item = None
        try:
            self._row_to_item.clear()
            self._item_to_row.clear()
        except Exception:
            pass
        try:
            for row in list(self._listbox.get_children() or []):
                try:
                    self._listbox.remove(row)
                except Exception:
                    pass
        except Exception:
            pass

    def changedItem(self):
        return getattr(self, "_changed_item", None)

    def _set_backend_enabled(self, enabled):
        """Enable/disable the GTK table at runtime."""
        try:
            if getattr(self, "_backend_widget", None) is not None and hasattr(self._backend_widget, "set_sensitive"):
                self._backend_widget.set_sensitive(bool(enabled))
        except Exception:
            pass
        try:
            if getattr(self, "_listbox", None) is not None and hasattr(self._listbox, "set_sensitive"):
                self._listbox.set_sensitive(bool(enabled))
        except Exception:
            pass
