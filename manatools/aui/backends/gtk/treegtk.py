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


class YTreeGtk(YSelectionWidget):
    """
    Stable Gtk4 implementation of a tree using Gtk.ListBox + ScrolledWindow.

    - Renders visible nodes (respecting YTreeItem._is_open).
    - Supports multiselection and recursiveSelection (select/deselect parents -> children).
    - Preserves stretching: the ScrolledWindow/ListBox expand to fill container.
    """
    def __init__(self, parent=None, label="", multiselection=False, recursiveselection=False):
        super().__init__(parent)
        self._label = label
        self._multi = bool(multiselection)
        self._recursive = bool(recursiveselection)
        if self._recursive:
            # recursive selection implies multi-selection semantics
            self._multi = True
        self._immediate = self.notify()
        self._backend_widget = None
        self._listbox = None
        # cached rows and mappings
        self._rows = []               # ordered list of Gtk.ListBoxRow
        self._row_to_item = {}        # row -> YTreeItem
        self._item_to_row = {}        # YTreeItem -> row
        self._visible_items = []      # list of (item, depth)
        self._suppress_selection_handler = False
        self._last_selected_ids = set()
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)

    def widgetClass(self):
        return "YTree"

    def _create_backend_widget(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        if self._label:
            try:
                lbl = Gtk.Label(label=self._label)
                if hasattr(lbl, "set_xalign"):
                    lbl.set_xalign(0.0)
                vbox.append(lbl)
            except Exception:
                pass

        # ListBox (flat, shows only visible nodes). Put into ScrolledWindow so it won't grow parent on expand.
        listbox = Gtk.ListBox()
        try:
            mode = Gtk.SelectionMode.MULTIPLE if self._multi else Gtk.SelectionMode.SINGLE
            listbox.set_selection_mode(mode)
            # Let listbox expand in available area
            listbox.set_vexpand(self.stretchable(YUIDimension.YD_VERT))
            listbox.set_hexpand(self.stretchable(YUIDimension.YD_HORIZ))
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

        # Make scrolled window expand to fill container (so tree respects parent stretching)
        try:
            sw.set_vexpand(self.stretchable(YUIDimension.YD_VERT))
            sw.set_hexpand(self.stretchable(YUIDimension.YD_HORIZ))
            vbox.set_vexpand(self.stretchable(YUIDimension.YD_VERT))
            vbox.set_hexpand(self.stretchable(YUIDimension.YD_HORIZ))
        except Exception:
            pass

        # connect selection signal; use defensive handler that scans rows
        try:
            listbox.connect("row-selected", lambda lb, row: self._on_row_selected(lb, row))
        except Exception:
            pass

        self._backend_widget = vbox
        self._listbox = listbox

        try:
            vbox.append(sw)
        except Exception:
            try:
                vbox.add(sw)
            except Exception:
                pass

        # populate if items already exist
        try:
            if getattr(self, "_items", None):
                self.rebuildTree()
        except Exception:
            pass

    def _make_row(self, item, depth):
        """Create a ListBoxRow for item with indentation and (optional) toggle button."""
        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # indentation spacer
        try:
            indent = Gtk.Box()
            indent.set_size_request(depth * 12, 1)
            hbox.append(indent)
        except Exception:
            pass

        # toggle if item has children
        has_children = False
        try:
            childs = []
            if callable(getattr(item, "children", None)):
                childs = item.children() or []
            else:
                childs = getattr(item, "_children", []) or []
            has_children = len(childs) > 0
        except Exception:
            has_children = False

        if has_children:
            try:
                btn = Gtk.Button(label="▾" if bool(getattr(item, "_is_open", False)) else "▸")
                try:
                    btn.set_relief(Gtk.ReliefStyle.NONE)
                except Exception:
                    pass
                # prevent the toggle button from taking focus / causing selection side-effects
                try:
                    btn.set_focus_on_click(False)
                except Exception:
                    pass
                try:
                    btn.set_can_focus(False)
                except Exception:
                    pass
                # make button visually flat (no border/background) so it looks like a tree expander
                try:
                    btn.add_css_class("flat")
                except Exception:
                    # fallback: try another common class name
                    try:
                        btn.add_css_class("link")
                    except Exception:
                        pass

                # Use a GestureClick on the button to reliably receive a single-click action
                # and avoid the occasional need for double clicks caused by focus/selection interplay.
                try:
                    gesture = Gtk.GestureClick()
                    # accept any button; if set_button exists restrict to primary
                    try:
                        gesture.set_button(0)
                    except Exception:
                        pass
                    # pressed handler will toggle immediately
                    def _on_pressed(gesture_obj, n_press, x, y, target_item=item):
                        # run toggle synchronously and suppress selection handler while rebuilding
                        try:
                            self._suppress_selection_handler = True
                        except Exception:
                            pass
                        try:
                            # toggle using public API if available
                            try:
                                cur = target_item.isOpen()
                                target_item.setOpen(not cur)
                            except Exception:
                                try:
                                    cur = bool(getattr(target_item, "_is_open", False))
                                    target_item._is_open = not cur
                                except Exception:
                                    pass
                            # preserve selection and rebuild
                            try:
                                self._last_selected_ids = set(id(i) for i in getattr(self, "_selected_items", []) or [])
                            except Exception:
                                self._last_selected_ids = set()
                            try:
                                self.rebuildTree()
                            except Exception:
                                pass
                        finally:
                            try:
                                self._suppress_selection_handler = False
                            except Exception:
                                pass

                    gesture.connect("pressed", _on_pressed)
                    try:
                        btn.add_controller(gesture)
                    except Exception:
                        try:
                            btn.add_controller(gesture)
                        except Exception:
                            pass
                except Exception:
                    # Fallback to clicked if GestureClick not available
                    try:
                        btn.connect("clicked", lambda b, it=item: self._on_toggle_clicked(it))
                    except Exception:
                        pass
                hbox.append(btn)
            except Exception:
                # fallback spacer
                try:
                    spacer = Gtk.Box()
                    spacer.set_size_request(14, 1)
                    hbox.append(spacer)
                except Exception:
                    pass
        else:
            try:
                spacer = Gtk.Box()
                spacer.set_size_request(14, 1)
                hbox.append(spacer)
            except Exception:
                pass

        # label
        try:
            lbl = Gtk.Label(label=item.label() if hasattr(item, "label") else str(item))
            if hasattr(lbl, "set_xalign"):
                lbl.set_xalign(0.0)
            # ensure label expands to take remaining space
            try:
                lbl.set_hexpand(True)
            except Exception:
                pass
            hbox.append(lbl)
        except Exception:
            pass

        try:
            row.set_child(hbox)
        except Exception:
            try:
                row.add(hbox)
            except Exception:
                pass

        try:
            row.set_selectable(True)
        except Exception:
            pass

        return row

    def _on_toggle_clicked(self, item):
        """Toggle _is_open and rebuild, preserving selection."""
        try:
            # Ensure a single-click toggle: suppress selection events during the operation
            try:
                self._suppress_selection_handler = True
            except Exception:
                pass
            try:
                try:
                    cur = item.isOpen()
                    item.setOpen(not cur)
                except Exception:
                    try:
                        cur = bool(getattr(item, "_is_open", False))
                        item._is_open = not cur
                    except Exception:
                        pass
                # preserve selection ids and rebuild the visible rows
                try:
                    self._last_selected_ids = set(id(i) for i in getattr(self, "_selected_items", []) or [])
                except Exception:
                    self._last_selected_ids = set()
                try:
                    self.rebuildTree()
                except Exception:
                    pass
            finally:
                try:
                    self._suppress_selection_handler = False
                except Exception:
                    pass
        except Exception:
            pass

    def _collect_all_descendants(self, item):
        """Return set of all descendant items (recursive)."""
        out = set()
        stack = []
        try:
            for c in getattr(item, "_children", []) or []:
                stack.append(c)
        except Exception:
            pass
        while stack:
            cur = stack.pop()
            out.add(cur)
            try:
                for ch in getattr(cur, "_children", []) or []:
                    stack.append(ch)
            except Exception:
                pass
        return out

    def rebuildTree(self):
        """Flatten visible items according to _is_open and populate the ListBox."""
        if self._backend_widget is None or self._listbox is None:
            self._create_backend_widget()
        try:
            # clear listbox rows robustly: repeatedly remove first child until none remain
            try:
                while True:
                    first = None
                    try:
                        first = self._listbox.get_first_child()
                    except Exception:
                        # some bindings may return None / raise; try children()
                        try:
                            chs = self._listbox.get_children()
                            first = chs[0] if chs else None
                        except Exception:
                            first = None
                    if not first:
                        break
                    try:
                        self._listbox.remove(first)
                    except Exception:
                        try:
                            # fallback API
                            self._listbox.unbind_model()
                            break
                        except Exception:
                            break
            except Exception:
                pass

            self._rows = []
            self._row_to_item.clear()
            self._item_to_row.clear()
            self._visible_items = []

            # Depth-first traversal producing visible nodes only when ancestors are open
            def _visit(nodes, depth=0):
                for n in nodes:
                    self._visible_items.append((n, depth))
                    try:
                        is_open = bool(getattr(n, "_is_open", False))
                    except Exception:
                        is_open = False
                    if is_open:
                        try:
                            childs = []
                            if callable(getattr(n, "children", None)):
                                childs = n.children() or []
                            else:
                                childs = getattr(n, "_children", []) or []
                        except Exception:
                            childs = getattr(n, "_children", []) or []
                        if childs:
                            _visit(childs, depth + 1)

            roots = list(getattr(self, "_items", []) or [])
            _visit(roots, 0)

            # create rows
            for item, depth in self._visible_items:
                try:
                    row = self._make_row(item, depth)
                    self._listbox.append(row)
                    self._rows.append(row)
                    self._row_to_item[row] = item
                    self._item_to_row[item] = row
                except Exception:
                    pass

            # restore previous selection (visible rows only)
            try:
                if self._last_selected_ids:
                    self._suppress_selection_handler = True
                    try:
                        self._listbox.unselect_all()
                    except Exception:
                        pass
                    for row, item in list(self._row_to_item.items()):
                        try:
                            if id(item) in self._last_selected_ids:
                                try:
                                    row.set_selected(True)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    self._suppress_selection_handler = False
            except Exception:
                self._suppress_selection_handler = False

            # rebuild logical selected items from rows
            self._selected_items = []
            for row in self._rows:
                try:
                    if getattr(row, "get_selected", None):
                        sel = row.get_selected()
                    else:
                        sel = bool(getattr(row, "_selected_flag", False))
                    if sel:
                        it = self._row_to_item.get(row, None)
                        if it is not None:
                            self._selected_items.append(it)
                except Exception:
                    pass

            self._last_selected_ids = set(id(i) for i in self._selected_items)
        except Exception:
            pass

    def _row_is_selected(self, r):
        """Robust helper to detect whether a ListBoxRow is selected."""
        try:
            # preferred API
            sel = getattr(r, "get_selected", None)
            if callable(sel):
                return bool(sel())
        except Exception:
            pass
        try:
            props = getattr(r, "props", None)
            if props and hasattr(props, "selected"):
                return bool(getattr(props, "selected"))
        except Exception:
            pass
        # fallback: check whether the listbox reports this row as selected (some bindings)
        try:
            if self._listbox is not None and hasattr(self._listbox, "get_selected_rows"):
                rows = self._listbox.get_selected_rows() or []
                for rr in rows:
                    if rr is r:
                        return True
        except Exception:
            pass
        # last-resort flag
        return bool(getattr(r, "_selected_flag", False))

    def _gather_selected_rows(self):
        """Return list of selected ListBoxRow objects (visible rows)."""
        rows = []
        try:
            # prefer listbox API if available
            if self._listbox is not None and hasattr(self._listbox, "get_selected_rows"):
                try:
                    sel = self._listbox.get_selected_rows() or []
                    # If API returns Gtk.ListBoxRow-like objects, include them; otherwise fallback
                    for s in sel:
                        if s is None:
                            continue
                        # if path-like, ignore (we rely on visible rows)
                        if isinstance(s, type(self._rows[0])) if self._rows else False:
                            rows.append(s)
                    if rows:
                        return rows
                except Exception:
                    pass
            # fallback: scan our cached rows
            for r in list(self._rows or []):
                try:
                    if self._row_is_selected(r):
                        rows.append(r)
                except Exception:
                    pass
        except Exception:
            pass
        return rows

    def _apply_desired_ids_to_rows(self, desired_ids):
        """Set visible rows selected state to match desired_ids (ids of items)."""
        if self._listbox is None:
            return
        try:
            self._suppress_selection_handler = True
        except Exception:
            pass
        try:
            try:
                self._listbox.unselect_all()
            except Exception:
                # continue even if unsupported
                pass
            for row, it in list(self._row_to_item.items()):
                try:
                    target = id(it) in desired_ids
                    try:
                        row.set_selected(bool(target))
                    except Exception:
                        try:
                            setattr(row, "_selected_flag", bool(target))
                        except Exception:
                            pass
                except Exception:
                    pass
        finally:
            try:
                self._suppress_selection_handler = False
            except Exception:
                pass

    def _on_row_selected(self, listbox, row):
        """Handle selection change; update logical selected items reliably.

        When recursive selection is enabled and multi-selection is on,
        selecting/deselecting a parent will also select/deselect all its descendants.
        """
        # ignore if programmatic change in progress
        if self._suppress_selection_handler:
            return

        try:
            selected_rows = self._gather_selected_rows()

            # map rows -> items
            cur_selected_items = []
            for r in selected_rows:
                try:
                    it = self._row_to_item.get(r, None)
                    if it is not None:
                        cur_selected_items.append(it)
                except Exception:
                    pass

            prev_ids = set(self._last_selected_ids or [])
            cur_ids = set(id(i) for i in cur_selected_items)
            added = cur_ids - prev_ids
            removed = prev_ids - cur_ids

            # If recursive+multi, compute desired ids by adding descendants of added and removing descendants of removed.
            desired_ids = set(cur_ids)
            if self._recursive and self._multi and (added or removed):
                try:
                    # add descendants of newly added items
                    for a in list(added):
                        # find object
                        obj = None
                        for it in cur_selected_items:
                            if id(it) == a:
                                obj = it
                                break
                        if obj is None:
                            # try to find in whole tree
                            def _find_by_id(tid, nodes):
                                for n in nodes:
                                    if id(n) == tid:
                                        return n
                                    try:
                                        chs = callable(getattr(n, "children", None)) and n.children() or getattr(n, "_children", []) or []
                                    except Exception:
                                        chs = getattr(n, "_children", []) or []
                                    r = _find_by_id(tid, chs)
                                    if r:
                                        return r
                                return None
                            obj = _find_by_id(a, list(getattr(self, "_items", []) or []))
                        if obj is not None:
                            for d in self._collect_all_descendants(obj):
                                desired_ids.add(id(d))

                    # remove descendants of removed items
                    for r_id in list(removed):
                        try:
                            obj = None
                            # try find in tree
                            def _find_by_id2(tid, nodes):
                                for n in nodes:
                                    if id(n) == tid:
                                        return n
                                    try:
                                        chs = callable(getattr(n, "children", None)) and n.children() or getattr(n, "_children", []) or []
                                    except Exception:
                                        chs = getattr(n, "_children", []) or []
                                    rr = _find_by_id2(tid, chs)
                                    if rr:
                                        return rr
                                return None
                            obj = _find_by_id2(r_id, list(getattr(self, "_items", []) or []))
                            if obj is not None:
                                for d in self._collect_all_descendants(obj):
                                    if id(d) in desired_ids:
                                        desired_ids.discard(id(d))
                        except Exception:
                            pass

                except Exception:
                    pass

                # Apply desired selection to visible rows
                try:
                    self._apply_desired_ids_to_rows(desired_ids)
                except Exception:
                    pass

                # Recompute cur_selected_items including non-visible descendants
                new_selected = []
                try:
                    # visible rows
                    for r in list(self._rows or []):
                        try:
                            if self._row_is_selected(r):
                                it = self._row_to_item.get(r)
                                if it is not None:
                                    new_selected.append(it)
                        except Exception:
                            pass
                    # include non-visible nodes that are requested by desired_ids
                    def _collect_all_nodes(nodes):
                        out = []
                        for n in nodes:
                            out.append(n)
                            try:
                                chs = callable(getattr(n, "children", None)) and n.children() or getattr(n, "_children", []) or []
                            except Exception:
                                chs = getattr(n, "_children", []) or []
                            if chs:
                                out.extend(_collect_all_nodes(chs))
                        return out
                    for root in list(getattr(self, "_items", []) or []):
                        for n in _collect_all_nodes([root]):
                            try:
                                if id(n) in desired_ids and n not in new_selected:
                                    new_selected.append(n)
                            except Exception:
                                pass
                    cur_selected_items = new_selected
                    cur_ids = set(id(i) for i in cur_selected_items)
                except Exception:
                    pass

            # Update logical selection flags
            try:
                def _clear_flags(nodes):
                    for n in nodes:
                        try:
                            n.setSelected(False)
                        except Exception:
                            pass
                        try:
                            chs = callable(getattr(n, "children", None)) and n.children() or getattr(n, "_children", []) or []
                        except Exception:
                            chs = getattr(n, "_children", []) or []
                        if chs:
                            _clear_flags(chs)
                _clear_flags(list(getattr(self, "_items", []) or []))
            except Exception:
                pass

            for it in cur_selected_items:
                try:
                    it.setSelected(True)
                except Exception:
                    pass

            # store logical selection
            self._selected_items = list(cur_selected_items)
            self._last_selected_ids = set(id(i) for i in self._selected_items)

            # notify immediate mode
            if self._immediate and self.notify():
                try:
                    dlg = self.findDialog()
                    if dlg:
                        dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
                except Exception:
                    pass
        except Exception:
            pass

    def currentItem(self):
        try:
            return self._selected_items[0] if self._selected_items else None
        except Exception:
            return None

    def getSelectedItem(self):
        return self.currentItem()

    def getSelectedItems(self):
        return list(self._selected_items)

    def activate(self):
        try:
            itm = self.currentItem()
            if itm is None:
                return False
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
            return True
        except Exception:
            return False

    def hasMultiSelection(self):
        """Return True if the tree allows selecting multiple items at once."""
        return bool(self._multi)

    def immediateMode(self):
        return bool(self._immediate)

    def setImmediateMode(self, on:bool=True):
        self._immediate = on
        self.setNotify(on)

    def _set_backend_enabled(self, enabled):
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            for it in list(getattr(self, "_items", []) or []):
                try:
                    if hasattr(it, "setEnabled"):
                        it.setEnabled(enabled)
                except Exception:
                    pass
        except Exception:
            pass

    def get_backend_widget(self):
        if self._backend_widget is None:
            self._create_backend_widget()
        return self._backend_widget
