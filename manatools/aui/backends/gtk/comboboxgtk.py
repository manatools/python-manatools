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


class YComboBoxGtk(YSelectionWidget):
    def __init__(self, parent=None, label="", editable=False):
        super().__init__(parent)
        self._label = label
        self._editable = editable
        self._value = ""
        self._selected_items = []
        self._combo_widget = None
    
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
                    model = Gtk.StringList()
                    for it in self._items:
                        model.append(it.label())
                    dropdown = Gtk.DropDown.new(model, None)
                    # select initial value
                    if self._value:
                        for idx, it in enumerate(self._items):
                            if it.label() == self._value:
                                dropdown.set_selected(idx)
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
        try:
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

            # update selected_items using reliable labels
            self._selected_items = [it for it in self._items if it.label() == self._value][:1]
        except Exception:
            pass

        if self.notify():
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
