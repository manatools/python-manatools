# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.gtk contains all GTK backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
'''

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, GObject, GdkPixbuf, GLib
import cairo
import threading
import os
from ...yui_common import *


class YSelectionBoxGtk(YSelectionWidget):
    def __init__(self, parent=None, label=""):
        super().__init__(parent)
        self._label = label
        self._value = ""
        self._selected_items = []
        self._multi_selection = False
        self._listbox = None
        self._backend_widget = None
        # keep a stable list of rows we create so we don't rely on ListBox container APIs
        # (GTK4 bindings may not expose get_children())
        self._rows = []
        # Preferred visible rows for layout/paging; parent can give more space when stretchable
        self._preferred_rows = 6
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)

    def widgetClass(self):
        return "YSelectionBox"

    def label(self):
        return self._label

    def value(self):
        return self._value

    def setValue(self, text):
        """Select first item matching text."""
        self._value = text
        self._selected_items = [it for it in self._items if it.label() == text]
        if self._listbox is None:
            return
        # find and select corresponding row using the cached rows list
        for i, row in enumerate(getattr(self, "_rows", [])):
            if i >= len(self._items):
                continue
            try:
                if self._items[i].label() == text:
                    row.set_selectable(True)
                    row.set_selected(True)
                else:
                    # ensure others are not selected in single-selection mode
                    if not self._multi_selection:
                        row.set_selected(False)
            except Exception:
                pass

        # rebuild internal selection state and notify
        try:
            self._selected_items = []
            for i, r in enumerate(getattr(self, "_rows", [])):
                try:
                    if self._row_is_selected(r) and i < len(self._items):
                        self._selected_items.append(self._items[i])
                except Exception:
                    pass
            self._value = self._selected_items[0].label() if self._selected_items else None
        except Exception:
            self._selected_items = []
            self._value = None

        if self.notify():
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))

    def selectedItems(self):
        return list(self._selected_items)

    def selectItem(self, item, selected=True):
        if selected:
            if not self._multi_selection:
                self._selected_items = [item]
                self._value = item.label()
            else:
                if item not in self._selected_items:
                    self._selected_items.append(item)
        else:
            if item in self._selected_items:
                self._selected_items.remove(item)
                self._value = self._selected_items[0].label() if self._selected_items else ""

        if self._listbox is None:
            return

        # reflect change in UI
        rows = getattr(self, "_rows", [])
        for i, it in enumerate(self._items):
            if it is item or it.label() == item.label():
                try:
                    row = rows[i]
                    row.set_selected(selected)
                except Exception:
                    pass
                break
        # rebuild internal selection state and notify
        try:
            self._selected_items = []
            for i, r in enumerate(getattr(self, "_rows", [])):
                try:
                    if self._row_is_selected(r) and i < len(self._items):
                        self._selected_items.append(self._items[i])
                except Exception:
                    pass
            self._value = self._selected_items[0].label() if self._selected_items else None
        except Exception:
            self._selected_items = []
            self._value = None

        if self.notify():
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))

    def setMultiSelection(self, enabled):
        self._multi_selection = bool(enabled)
        # If listbox already created, update its selection mode at runtime.
        if self._listbox is None:
            return
        try:
            mode = Gtk.SelectionMode.MULTIPLE if self._multi_selection else Gtk.SelectionMode.SINGLE
            self._listbox.set_selection_mode(mode)
        except Exception:
            pass
        # Rewire signals: disconnect previous handlers and connect appropriate one.
        try:
            # Disconnect any previously stored handlers
            try:
                for key, hid in list(getattr(self, "_signal_handlers", {}).items()):
                    if hid and isinstance(hid, int):
                        try:
                            self._listbox.disconnect(hid)
                        except Exception:
                            pass
                self._signal_handlers = {}
            except Exception:
                self._signal_handlers = {}

            # Connect new handler based on mode
            if self._multi_selection:
                try:
                    hid = self._listbox.connect("selected-rows-changed", lambda lb: self._on_selected_rows_changed(lb))                    
                    self._signal_handlers['selected-rows-changed'] = hid
                except Exception:
                    try:
                        hid = self._listbox.connect("row-selected", lambda lb, row: self._on_selected_rows_changed(lb))
                        self._signal_handlers['row-selected_for_multi'] = hid
                    except Exception:
                        pass
            else:
                try:
                    hid = self._listbox.connect("row-selected", lambda lb, row: self._on_row_selected(lb, row))
                    self._signal_handlers['row-selected'] = hid
                except Exception:
                    pass
        except Exception:
            pass

    def multiSelection(self):
        return bool(self._multi_selection)

    def _create_backend_widget(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        if self._label:
            lbl = Gtk.Label(label=self._label)
            try:
                if hasattr(lbl, "set_xalign"):
                    lbl.set_xalign(0.0)
            except Exception:
                pass
            try:
                vbox.append(lbl)
            except Exception:
                vbox.add(lbl)

        # Use Gtk.ListBox inside a ScrolledWindow for Gtk4
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE if self._multi_selection else Gtk.SelectionMode.SINGLE)
        # allow listbox to expand if parent allocates more space
        try:
            listbox.set_vexpand(self.stretchable(YUIDimension.YD_VERT))
            listbox.set_hexpand(self.stretchable(YUIDimension.YD_HORIZ))
        except Exception:
            pass
        # populate rows
        self._rows = []
        for it in self._items:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=it.label() or "")
            try:
                if hasattr(lbl, "set_xalign"):
                    lbl.set_xalign(0.0)
            except Exception:
                pass
            try:
                row.set_child(lbl)
            except Exception:
                try:
                    row.add(lbl)
                except Exception:
                    pass

            # Make every row selectable so users can multi-select if mode allows.
            try:
                row.set_selectable(True)
            except Exception:
                pass
            
            # If this item matches current value, mark selected
            try:
                if self._value and it.label() == self._value:
                    row.set_selectable(True)
                    row.set_selected(True)
            except Exception:
                pass
            self._rows.append(row)
            listbox.append(row)

        # Reflect items' selected flags into the view/model.
        try:
            if self._multi_selection:
                for idx, it in enumerate(self._items):
                    try:
                        if it.selected():
                            try:
                                self._rows[idx].set_selected(True)
                            except Exception:
                                try:
                                    setattr(self._rows[idx], '_selected_flag', True)
                                except Exception:
                                    pass
                            if it not in self._selected_items:
                                self._selected_items.append(it)
                            if not self._value:
                                self._value = it.label()
                    except Exception:
                        pass
            else:
                last_selected_idx = None
                for idx, it in enumerate(self._items):
                    try:
                        if it.selected():
                            last_selected_idx = idx
                    except Exception:
                        pass
                if last_selected_idx is not None:
                    try:
                        for i, r in enumerate(self._rows):
                            try:
                                if i == last_selected_idx:
                                    listbox.select_row( r )                                
                            except Exception:
                                try:
                                    setattr(r, '_selected_flag', (i == last_selected_idx))
                                except Exception:
                                    pass
                        try:
                            for i, it in enumerate(self._items):
                                try:
                                    it.setSelected(i == last_selected_idx)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        self._selected_items = [self._items[last_selected_idx]]
                        self._value = self._items[last_selected_idx].label()
                    except Exception:
                        pass
        except Exception:
            pass

        sw = Gtk.ScrolledWindow()
        # allow scrolled window to expand vertically and horizontally
        try:
            sw.set_vexpand(self.stretchable(YUIDimension.YD_VERT))
            sw.set_hexpand(self.stretchable(YUIDimension.YD_HORIZ))
            # give a reasonable minimum content height so layout initially shows several rows;
            # Gtk4 expects pixels — try a conservative estimate (rows * ~20px)
            min_h = int(getattr(self, "_preferred_rows", 6) * 20)
            try:
                # some Gtk4 bindings expose set_min_content_height
                sw.set_min_content_height(min_h)
            except Exception:
                pass
        except Exception:
            pass
        # policy APIs changed in Gtk4: use set_overlay_scrolling and set_min_content_height if needed
        try:
            sw.set_child(listbox)
        except Exception:
            try:
                sw.add(listbox)
            except Exception:
                pass

        # also request vexpand on the outer vbox so parent layout sees it can grow
        try:
            vbox.set_vexpand(self.stretchable(YUIDimension.YD_VERT))
            vbox.set_hexpand(self.stretchable(YUIDimension.YD_HORIZ))
        except Exception:
            pass

        try:
            vbox.append(sw)
        except Exception:
            vbox.add(sw)

        # connect selection signal: choose appropriate signal per selection mode
        # store handler ids so we can disconnect later if selection mode changes at runtime
        self._signal_handlers = {}
        try:
            # ensure any previous handlers are disconnected (defensive)
            try:
                for hid in list(self._signal_handlers.values()):
                    if hid and isinstance(hid, int):
                        try:
                            listbox.disconnect(hid)
                        except Exception:
                            pass
            except Exception:
                pass

            # Use row-selected for both single and multi modes; handler will toggle for multi
            try:
                hid = listbox.connect("row-selected", lambda lb, row: self._on_row_selected(lb, row))
                self._signal_handlers['row-selected'] = hid
            except Exception:
                pass
        except Exception:
            pass

        self._backend_widget = vbox
        self._listbox = listbox
        self._backend_widget.set_sensitive(self._enabled)

    def _set_backend_enabled(self, enabled):
        """Enable/disable the selection box and its listbox/rows."""
        try:
            if getattr(self, "_listbox", None) is not None:
                try:
                    self._listbox.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass
        # propagate logical enabled state to child items/widgets
        try:
            for c in list(getattr(self, "_rows", []) or []):
                try:
                    c.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass

    def _row_is_selected(self, r):
        """Robust helper to detect whether a ListBoxRow is selected."""
        try:
            return bool(r.get_selected())
        except Exception:
            pass
        try:
            props = getattr(r, "props", None)
            if props and hasattr(props, "selected"):
                return bool(getattr(props, "selected"))
        except Exception:
            pass
        return bool(getattr(r, "_selected_flag", False))

    def _on_row_selected(self, listbox, row):
        """
        Handler for row selection. In single-selection mode behaves as before
        (select provided row and deselect others). In multi-selection mode toggles
        the provided row and rebuilds the selected items list.
        """
        try:
            #if row is not None:
            #    if self._multi_selection:
            #        # toggle selection state for this row
            #        try:
            #            cur = self._row_is_selected(row)
            #            try:
            #                if not cur:
            #                    self._listbox.select_row( row )
            #            except Exception:
            #                # fallback: store a flag when set_selected isn't available
            #                setattr(row, "_selected_flag", not cur)
            #        except Exception:
            #            pass
            #    else:
            #        # single-selection: select provided row and deselect others
            #        for r in getattr(self, "_rows", []):
            #            try:
            #                if r is row:
            #                    self._listbox.select_row( r )
            #            except Exception:
            #                try:
            #                    setattr(r, "_selected_flag", (r is row))
            #                except Exception:
            #                    pass

            # rebuild selected_items scanning cached rows (works for both modes)
            self._selected_items = []
            for i, r in enumerate(getattr(self, "_rows", [])):
                try:
                    if row is r and i < len(self._items):
                        self._selected_items.append(self._items[i])
                        self._items[i].setSelected( True )
                except Exception:
                    print("Failed to check row selection")
                    pass

            self._value = self._selected_items[0].label() if self._selected_items else None
        except Exception:
            # be defensive
            self._selected_items = []
            self._value = None

        if self.notify():
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))

    def _on_selected_rows_changed(self, listbox):
        """
        Handler for multi-selection (or bulk selection change). Rebuild selected list
        using either ListBox APIs (if available) or by scanning cached rows.
        """
        try:
            # Try to use any available API that returns selected rows
            sel_rows = None
            try:
                # Some bindings may provide get_selected_rows()
                sel_rows = listbox.get_selected_rows()
                print(f"Using get_selected_rows() {len(sel_rows)} API")
            except Exception:
                sel_rows = None

            self._selected_items = []
            if sel_rows:
                # sel_rows may be list of Row objects or Paths; try to match by identity
                for r in sel_rows:
                    try:
                        # if r is a ListBoxRow already
                        if isinstance(r, type(self._rows[0])) if self._rows else False:
                            try:
                                idx = self._rows.index(r)
                                if idx < len(self._items):
                                    self._selected_items.append(self._items[idx])
                            except Exception:
                                pass
                        else:
                            # fallback: scan cached rows to find selected ones
                            for i, cr in enumerate(getattr(self, "_rows", [])):
                                try:
                                    if self._row_is_selected(cr) and i < len(self._items):
                                        self._selected_items.append(self._items[i])
                                except Exception:
                                    pass
                    except Exception:
                        pass
            else:
                # Generic fallback: scan cached rows and collect selected ones
                for i, r in enumerate(getattr(self, "_rows", [])):
                    try:
                        if self._row_is_selected(r) and i < len(self._items):
                            self._selected_items.append(self._items[i])
                    except Exception:
                        pass

            self._value = self._selected_items[0].label() if self._selected_items else None
        except Exception:
            self._selected_items = []
            self._value = None

        if self.notify():
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))


    def deleteAllItems(self):
        """Remove all items from the selection box (model + GTK view)."""
        # Clear internal model
        super().deleteAllItems()
        self._value = ""
        self._selected_items = []

        # Clear GTK rows/listbox
        try:
            rows = list(getattr(self, '_rows', []) or [])
            for r in rows:
                try:
                    if getattr(self, '_listbox', None) is not None:
                        try:
                            self._listbox.remove(r)
                        except Exception:
                            try:
                                # fallback: unparent the row
                                r.unparent()
                            except Exception:
                                pass
                except Exception:
                    pass
            self._rows = []
        except Exception:
            pass

    def addItem(self, item):
        """Add a single item to the selection box (model + GTK view)."""
        super().addItem(item)
        try:
            new_item = self._items[-1]
        except Exception:
            return

        try:
            new_item.setIndex(len(self._items) - 1)
        except Exception:
            pass

        # If listbox exists, create a new row and append
        try:
            if getattr(self, '_listbox', None) is not None:
                row = Gtk.ListBoxRow()
                lbl = Gtk.Label(label=new_item.label() or "")
                try:
                    if hasattr(lbl, "set_xalign"):
                        lbl.set_xalign(0.0)
                except Exception:
                    pass
                try:
                    row.set_child(lbl)
                except Exception:
                    try:
                        row.add(lbl)
                    except Exception:
                        pass
                try:
                    row.set_selectable(True)
                except Exception:
                    pass

                # append the row first so selection APIs operate on attached rows
                try:
                    try:
                        self._listbox.append(row)
                    except Exception:
                        try:
                            self._listbox.add(row)
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    self._rows.append(row)
                except Exception:
                    pass

                # reflect selected state (no notification on add)
                try:
                    if new_item.selected():
                        # single-selection: clear previous selections
                        if not self._multi_selection:
                            try:
                                for r in getattr(self, '_rows', []):
                                    try:
                                        self._listbox.unselect_row( r )
                                        #r.set_selected(False)
                                    except Exception:
                                        print("Failed to deselect row")
                                        try:
                                            setattr(r, '_selected_flag', False)
                                        except Exception:
                                            pass
                            except Exception:
                                pass
                            try:
                                for it in self._items[:-1]:
                                    try:
                                        it.setSelected(False)
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                        try:
                            self._listbox.select_row( row )
                        except Exception:
                            try:
                                setattr(row, '_selected_flag', True)
                            except Exception:
                                pass

                        try:
                            new_item.setSelected(True)
                        except Exception:
                            pass

                        if new_item not in self._selected_items:
                            self._selected_items.append(new_item)
                        if not self._value:
                            self._value = new_item.label()
                except Exception:
                    pass
        except Exception:
            pass

