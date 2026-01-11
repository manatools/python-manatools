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
    """
    GTK4 backend for a simple combo/select widget.
    Provides editable and non-editable variants using Gtk.Entry, Gtk.DropDown or a simple cycling Gtk.Button.
    Uses logging extensively to surface runtime issues and fallbacks.
    """
    def __init__(self, parent=None, label="", editable=False):
        """
        Initialize backend combobox.
        - parent: parent widget
        - label: optional label text
        - editable: if True use an Entry, otherwise use DropDown or fallback
        """
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
        """
        Set the current displayed value (tries to update backing GTK widget).
        Logs any exceptions encountered while updating the GTK widget.
        """
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
                self._logger.exception("setValue: failed to update backend widget with text=%r", text)

    def editable(self):
        return self._editable
    
    def _create_backend_widget(self):
        """
        Create GTK widgets backing the combo: label + entry/dropdown/button.
        Uses conservative fallbacks and logs failures for diagnostics.
        """
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        if self._label:
            label = Gtk.Label(label=self._label)
            try:
                if hasattr(label, "set_xalign"):
                    label.set_xalign(0.0)
            except Exception:
                self._logger.exception("_create_backend_widget: label.set_xalign failed")
            try:
                hbox.append(label)
            except Exception:
                try:
                    hbox.add(label)
                except Exception:
                    self._logger.exception("_create_backend_widget: failed to add label to hbox")

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
                try:
                    hbox.add(entry)
                except Exception:
                    self._logger.exception("_create_backend_widget: failed to add editable entry to hbox")
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
                            self._logger.exception("_create_backend_widget: error checking item.selected() for index %d", idx)
                    if selected_idx >= 0:
                        try:
                            dropdown.set_selected(selected_idx)
                            self._value = self._items[selected_idx].label()
                            self._selected_items = [self._items[selected_idx]]
                        except Exception:
                            self._logger.exception("_create_backend_widget: failed to set selected index %d", selected_idx)
                    else:
                        # fallback to explicit value string if provided
                        if self._value:
                            for idx, it in enumerate(self._items):
                                try:
                                    if it.label() == self._value:
                                        dropdown.set_selected(idx)
                                        self._selected_items = [it]
                                        break
                                except Exception:
                                    self._logger.exception("_create_backend_widget: matching value to items failed at index %d", idx)
                    try:
                        dropdown.connect("notify::selected", lambda w, pspec: self._on_changed_dropdown(w))
                        self._combo_widget = dropdown
                        hbox.append(dropdown)
                    except Exception:
                        self._logger.exception("_create_backend_widget: failed to connect/append dropdown")
                else:
                     # fallback: simple Gtk.Button that cycles items on click (very simple)
                    btn = Gtk.Button(label=self._value or (self._items[0].label() if self._items else ""))
                    btn.connect("clicked", self._on_fallback_button_clicked)
                    self._combo_widget = btn
                    try:
                        hbox.append(btn)
                    except Exception:
                        try:
                            hbox.add(btn)
                        except Exception:
                            self._logger.exception("_create_backend_widget: failed to add fallback button")
            except Exception:
                # final fallback: entry
                self._logger.exception("_create_backend_widget: unexpected failure building non-editable control; falling back to Entry")
                entry = Gtk.Entry()
                entry.set_text(self._value)
                entry.connect("changed", self._on_text_changed)
                self._combo_widget = entry
                try:
                    hbox.append(entry)
                except Exception:
                    try:
                        hbox.add(entry)
                    except Exception:
                        self._logger.exception("_create_backend_widget: failed to add fallback entry")

        self._backend_widget = hbox
        try:
            self._backend_widget.set_sensitive(self._enabled)
        except Exception:
            self._logger.exception("_create_backend_widget: failed to set backend widget sensitivity")
        # Allow logger to raise if misconfigured so failures are visible during debugging
        self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())

    def _set_backend_enabled(self, enabled):
        """
        Enable/disable the combobox/backing widget and its entry/dropdown.
        Logs problems when setting sensitivity fails.
        """
        try:
            # prefer to enable the primary control if present
            ctl = getattr(self, "_combo_widget", None)
            if ctl is not None:
                try:
                    ctl.set_sensitive(enabled)
                except Exception:
                    self._logger.exception("_set_backend_enabled: failed to set_sensitive on primary control")
        except Exception:
            self._logger.exception("_set_backend_enabled: error accessing primary control")
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    self._logger.exception("_set_backend_enabled: failed to set_sensitive on backend widget")
        except Exception:
            self._logger.exception("_set_backend_enabled: error accessing backend widget")

    def _on_fallback_button_clicked(self, btn):
        """
        Cycle through items when using the fallback button control.
        Logs unexpected issues.
        """
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
        try:
            btn.set_label(new)
            self.setValue(new)
            if self.notify():
                dlg = self.findDialog()
                if dlg:
                    dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
        except Exception:
            self._logger.exception("_on_fallback_button_clicked: failed to cycle/set selection")

    def _on_text_changed(self, entry):
        """
        Handler for editable text changes. Updates internal value and notifies dialog.
        """
        try:
            text = entry.get_text()
        except Exception:
            text = ""
            self._logger.exception("_on_text_changed: failed to read entry text")
        self._value = text
        try:
            self._selected_items = [it for it in self._items if it.label() == self._value][:1]
        except Exception:
            self._logger.exception("_on_text_changed: error updating selected_items")
            self._selected_items = []
        if self.notify():
            try:
                dlg = self.findDialog()
                if dlg is not None:
                    dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
            except Exception:
                self._logger.exception("_on_text_changed: failed to notify dialog")

    def _on_changed_dropdown(self, dropdown):
        """
        Handler for Gtk.DropDown selection changes. Attempts robust extraction of selected label.
        """
        # Prefer using the selected index to get a reliable label
        idx = None
        try:
            idx = dropdown.get_selected()
        except Exception:
            idx = None
            self._logger.exception("_on_changed_dropdown: failed to get_selected() from dropdown")

        if isinstance(idx, int) and 0 <= idx < len(self._items):
            try:
                self._value = self._items[idx].label()
            except Exception:
                self._logger.exception("_on_changed_dropdown: failed to read label from items at index %d", idx)
                self._value = ""
        else:
            # Fallback: try to extract text from the selected-item object
            val = None
            try:
                val = dropdown.get_selected_item()
            except Exception:
                val = None
                self._logger.exception("_on_changed_dropdown: failed to get_selected_item()")

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
                        self._logger.debug("_on_changed_dropdown: accessor %s failed on selected item", meth)
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
                                    self._logger.debug("_on_changed_dropdown: props accessor %s failed", attr)
                    except Exception:
                        self._logger.exception("_on_changed_dropdown: error inspecting props on selected item")
                # final fallback to str()
                if not self._value:
                    try:
                        self._value = str(val)
                    except Exception:
                        self._value = ""
                        self._logger.exception("_on_changed_dropdown: str(selected_item) failed")

        # update selected_items and ensure only one item is selected in model
        self._selected_items = []
        for it in self._items:
            try:
                sel = (it.label() == self._value)
                it.setSelected(sel)
                if sel:
                    self._selected_items.append(it)
            except Exception:
                self._logger.exception("_on_changed_dropdown: failed updating selection for an item")

        if self.notify():
            try:
                dlg = self.findDialog()
                if dlg is not None:
                    dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
            except Exception:
                self._logger.exception("_on_changed_dropdown: failed to notify dialog")
        # Allow logger to raise if misconfigured so failures are visible during debugging
        self._logger.debug("_on_changed_dropdown: value=%s selected_items=%s", self._value, [it.label() for it in self._selected_items])

    # Runtime: add a single item (model + view)
    def addItem(self, item):
        """
        Add an item at runtime. Updates internal state and GTK backing model when possible.
        """
        try:
            super().addItem(item)
        except Exception:
            try:
                if isinstance(item, str):
                    super().addItem(item)
                else:
                    self._items.append(item)
                self._logger.debug("addItem: fallback appended item %r", item)
            except Exception:
                self._logger.exception("addItem: failed to add item %r", item)
                return
        try:
            new_item = self._items[-1]
            new_item.setIndex(len(self._items) - 1)
        except Exception:
            self._logger.exception("addItem: failed to set index on new item")
            return

        # ensure only one selected in combo semantics
        try:
            if new_item.selected():
                for it in self._items[:-1]:
                    try:
                        it.setSelected(False)
                    except Exception:
                        self._logger.exception("addItem: failed to clear selection on existing item")
                new_item.setSelected(True)
                self._value = new_item.label()
                self._selected_items = [new_item]
        except Exception:
            self._logger.exception("addItem: failed while enforcing single-selection semantics")

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
                        self._logger.exception("addItem: failed to update string_list_model with new item")
                else:
                    # fallback: update button label if single item and selected
                    try:
                        if getattr(self._combo_widget, "set_label", None) and new_item.selected():
                            self._combo_widget.set_label(new_item.label())
                    except Exception:
                        self._logger.exception("addItem: failed to update fallback combo widget label")
            except Exception:
                self._logger.exception("addItem: unexpected error while updating backend widget")

    def deleteAllItems(self):
        """
        Remove all items and reset backend widgets. Logs any issues so runtime problems are visible.
        """
        try:
            super().deleteAllItems()
        except Exception:
            self._logger.exception("deleteAllItems: super().deleteAllItems() failed")
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
                        self._logger.exception("deleteAllItems: failed to recreate string_list_model")
                elif isinstance(self._combo_widget, Gtk.Entry):
                    try:
                        self._combo_widget.set_text("")
                    except Exception:
                        self._logger.exception("deleteAllItems: failed to clear entry text")
                else:
                    try:
                        if getattr(self._combo_widget, "set_label", None):
                            self._combo_widget.set_label("")
                    except Exception:
                        self._logger.exception("deleteAllItems: failed to clear fallback widget label")
            except Exception:
                self._logger.exception("deleteAllItems: unexpected error while updating backend widget")
