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
import logging
from ...yui_common import *
from .commongtk import _resolve_icon


class YComboBoxGtk(YSelectionWidget):
    def __init__(self, parent=None, label="", editable=False):
        super().__init__(parent)
        self._label = label
        self._editable = editable
        self._value = ""
        self._selected_items = []
        self._combo_widget = None
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
    
    def widgetClass(self):
        return "YComboBox"
    
    def value(self):
        return self._value
    
    def setValue(self, text):
        self._value = text
        if self._combo_widget:
            try:
                # try entry child for editable combos
                child = None
                if self._editable:
                    child = self._combo_widget.get_child()
                if child and hasattr(child, "set_text"):
                    child.set_text(text)
                else:
                    # attempt to set active by matching text if API available
                    if hasattr(self._combo_widget, "set_active_id"):
                        # Gtk.DropDown uses ids in models; we keep simple and try to match by text
                        # fallback: rebuild model and select programmatically below
                        pass
                # update selected_items
                self._selected_items = [it for it in self._items if it.label() == text][:1]
            except Exception:
                pass

    def editable(self):
        return self._editable
    
    def _create_backend_widget(self):
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        if self._label:
            label = Gtk.Label(label=self._label)
            try:
                if hasattr(label, "set_xalign"):
                    label.set_xalign(0.0)
            except Exception:
                pass
            try:
                hbox.append(label)
            except Exception:
                hbox.add(label)

        # For Gtk4 there is no ComboBoxText; try DropDown for non-editable,
        # and Entry for editable combos (simple fallback).
        if self._editable:
            entry = Gtk.Entry()
            entry.set_text(self._value)
            entry.connect("changed", self._on_text_changed)
            self._combo_widget = entry
            try:
                hbox.append(entry)
            except Exception:
                hbox.add(entry)
        else:
            # Build a simple Gtk.DropDown backed by a Gtk.StringList (if available)
            try:
                if hasattr(Gtk, "StringList") and hasattr(Gtk, "DropDown"):
                    # keep model reference for runtime updates
                    self._string_list_model = Gtk.StringList()
                    for it in self._items:
                        self._string_list_model.append(it.label())
                    dropdown = Gtk.DropDown.new(self._string_list_model, None)
                    # prefer explicit selected item flag in model; only one allowed
                    selected_idx = -1
                    for idx, it in enumerate(self._items):
                        try:
                            if it.selected():
                                selected_idx = idx
                                break
                        except Exception:
                            pass
                    if selected_idx >= 0:
                        dropdown.set_selected(selected_idx)
                        self._value = self._items[selected_idx].label()
                        self._selected_items = [self._items[selected_idx]]
                    else:
                        # fallback to explicit value string if provided
                        if self._value:
                            for idx, it in enumerate(self._items):
                                if it.label() == self._value:
                                    dropdown.set_selected(idx)
                                    self._selected_items = [it]
                                    break
                    dropdown.connect("notify::selected", lambda w, pspec: self._on_changed_dropdown(w))
                    self._combo_widget = dropdown
                    hbox.append(dropdown)
                else:
                     # fallback: simple Gtk.Button that cycles items on click (very simple)
                    btn = Gtk.Button(label=self._value or (self._items[0].label() if self._items else ""))
                    btn.connect("clicked", self._on_fallback_button_clicked)
                    self._combo_widget = btn
                    hbox.append(btn)
            except Exception:
                # final fallback: entry
                entry = Gtk.Entry()
                entry.set_text(self._value)
                entry.connect("changed", self._on_text_changed)
                self._combo_widget = entry
                hbox.append(entry)

        self._backend_widget = hbox
        self._backend_widget.set_sensitive(self._enabled)
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        """Enable/disable the combobox/backing widget and its entry/dropdown."""
        try:
            # prefer to enable the primary control if present
            ctl = getattr(self, "_combo_widget", None)
            if ctl is not None:
                try:
                    ctl.set_sensitive(enabled)
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

    def _on_fallback_button_clicked(self, btn):
        # naive cycle through items
        if not self._items:
            return
        current = btn.get_label()
        labels = [it.label() for it in self._items]
        try:
            idx = labels.index(current)
            idx = (idx + 1) % len(labels)
        except Exception:
            idx = 0
        new = labels[idx]
        btn.set_label(new)
        self.setValue(new)
        if self.notify():
            dlg = self.findDialog()
            if dlg:
                dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))

    def _on_text_changed(self, entry):
        try:
            text = entry.get_text()
        except Exception:
            text = ""
        self._value = text
        self._selected_items = [it for it in self._items if it.label() == self._value][:1]
        if self.notify():
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))

    def _on_changed_dropdown(self, dropdown):
        # Prefer using the selected index to get a reliable label
        idx = None
        try:
            idx = dropdown.get_selected()
        except Exception:
            idx = None

        if isinstance(idx, int) and 0 <= idx < len(self._items):
            self._value = self._items[idx].label()
        else:
            # Fallback: try to extract text from the selected-item object
            val = None
            try:
                val = dropdown.get_selected_item()
            except Exception:
                val = None

            self._value = ""
            if isinstance(val, str):
                self._value = val
            elif val is not None:
                # Try common accessor names that GTK objects may expose
                for meth in ("get_string", "get_text", "get_value", "get_label", "get_name", "to_string"):
                    try:
                        fn = getattr(val, meth, None)
                        if callable(fn):
                            v = fn()
                            if isinstance(v, str) and v:
                                self._value = v
                                break
                    except Exception:
                        continue
                # Try properties if available
                if not self._value:
                    try:
                        props = getattr(val, "props", None)
                        if props:
                            for attr in ("string", "value", "label", "name", "text"):
                                try:
                                    pv = getattr(props, attr)
                                    if isinstance(pv, str) and pv:
                                        self._value = pv
                                        break
                                except Exception:
                                    pass
                    except Exception:
                        pass
                # final fallback to str()
                if not self._value:
                    try:
                        self._value = str(val)
                    except Exception:
                        self._value = ""

        # update selected_items and ensure only one item is selected in model
        self._selected_items = []
        for it in self._items:
            try:
                sel = (it.label() == self._value)
                it.setSelected(sel)
                if sel:
                    self._selected_items.append(it)
            except Exception:
                pass

        if self.notify():
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
        try:
            self._logger.debug("_on_changed_dropdown: value=%s selected_items=%s", self._value, [it.label() for it in self._selected_items])
        except Exception:
            pass

    # Runtime: add a single item (model + view)
    def addItem(self, item):
        try:
            super().addItem(item)
        except Exception:
            # fall back if super fails
            try:
                if isinstance(item, str):
                    super().addItem(item)
                else:
                    self._items.append(item)
            except Exception:
                return
        try:
            new_item = self._items[-1]
            new_item.setIndex(len(self._items) - 1)
        except Exception:
            return

        # ensure only one selected in combo semantics
        try:
            if new_item.selected():
                for it in self._items[:-1]:
                    try:
                        it.setSelected(False)
                    except Exception:
                        pass
                new_item.setSelected(True)
                self._value = new_item.label()
                self._selected_items = [new_item]
        except Exception:
            pass

        # update GTK backing widget
        if getattr(self, "_combo_widget", None):
            try:
                if isinstance(self._combo_widget, Gtk.Entry):
                    # nothing special: entries are freeform
                    pass
                elif hasattr(self, "_string_list_model") and isinstance(self._string_list_model, Gtk.StringList):
                    try:
                        self._string_list_model.append(new_item.label())
                        # if the new item was selected, update dropdown selection
                        if new_item.selected():
                            self._combo_widget.set_selected(len(self._string_list_model) - 1)
                    except Exception:
                        pass
                else:
                    # fallback: update button label if single item and selected
                    try:
                        if getattr(self._combo_widget, "set_label", None) and new_item.selected():
                            self._combo_widget.set_label(new_item.label())
                    except Exception:
                        pass
            except Exception:
                pass

    def deleteAllItems(self):
        super().deleteAllItems()
        self._value = ""
        # update GTK widgets
        if getattr(self, "_combo_widget", None):
            try:
                if hasattr(self, "_string_list_model") and isinstance(self._string_list_model, Gtk.StringList):
                    try:
                        # recreate model
                        self._string_list_model = Gtk.StringList()
                        self._combo_widget.set_model(self._string_list_model)
                    except Exception:
                        pass
                elif isinstance(self._combo_widget, Gtk.Entry):
                    try:
                        self._combo_widget.set_text("")
                    except Exception:
                        pass
                else:
                    try:
                        if getattr(self._combo_widget, "set_label", None):
                            self._combo_widget.set_label("")
                    except Exception:
                        pass
            except Exception:
                pass
