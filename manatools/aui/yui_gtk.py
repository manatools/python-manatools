"""
GTK backend implementation for YUI
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, GLib
import threading
from .yui_common import *

class YUIGtk:
    def __init__(self):
        self._widget_factory = YWidgetFactoryGtk()
        self._optional_widget_factory = None
        self._application = YApplicationGtk()
    
    def widgetFactory(self):
        return self._widget_factory
    
    def optionalWidgetFactory(self):
        return self._optional_widget_factory
    
    def app(self):
        return self._application
    
    def application(self):
        return self._application
    
    def yApp(self):
        return self._application

class YApplicationGtk:
    def __init__(self):
        self._icon_base_path = "/usr/share/icons"
        self._product_name = "YUI GTK"
    
    def iconBasePath(self):
        return self._icon_base_path
    
    def setIconBasePath(self, new_icon_base_path):
        self._icon_base_path = new_icon_base_path
    
    def setProductName(self, product_name):
        self._product_name = product_name
    
    def productName(self):
        return self._product_name

class YWidgetFactoryGtk:
    def __init__(self):
        pass
    
    def createMainDialog(self, color_mode=YDialogColorMode.YDialogNormalColor):
        return YDialogGtk(YDialogType.YMainDialog, color_mode)
    
    def createPopupDialog(self, color_mode=YDialogColorMode.YDialogNormalColor):
        return YDialogGtk(YDialogType.YPopupDialog, color_mode)
    
    def createVBox(self, parent):
        return YVBoxGtk(parent)
    
    def createHBox(self, parent):
        return YHBoxGtk(parent)
    
    def createPushButton(self, parent, label):
        return YPushButtonGtk(parent, label)
    
    def createLabel(self, parent, text, isHeading=False, isOutputField=False):
        return YLabelGtk(parent, text, isHeading, isOutputField)
    
    def createHeading(self, parent, label):
        return YLabelGtk(parent, label, isHeading=True)
    
    def createInputField(self, parent, label, password_mode=False):
        return YInputFieldGtk(parent, label, password_mode)
    
    def createCheckBox(self, parent, label, is_checked=False):
        return YCheckBoxGtk(parent, label, is_checked)
    
    def createPasswordField(self, parent, label):
        return YInputFieldGtk(parent, label, password_mode=True)
    
    def createComboBox(self, parent, label, editable=False):
        return YComboBoxGtk(parent, label, editable)

# GTK Widget Implementations
class YDialogGtk(YSingleChildContainerWidget):
    _open_dialogs = []
    
    def __init__(self, dialog_type=YDialogType.YMainDialog, color_mode=YDialogColorMode.YDialogNormalColor):
        super().__init__()
        self._dialog_type = dialog_type
        self._color_mode = color_mode
        self._is_open = False
        self._window = None
        self._event_result = None
        self._glib_loop = None
        YDialogGtk._open_dialogs.append(self)
    
    def widgetClass(self):
        return "YDialog"
    
    def open(self):
        # Finalize and show the dialog in a non-blocking way.
        # Matching libyui semantics: open() should finalize and make visible,
        # but must NOT start a global blocking Gtk.main() here.
        if not self._is_open:
            if not self._window:
                self._create_backend_widget()
            self._window.show_all()
            self._is_open = True
    
    def isOpen(self):
        return self._is_open
    
    def destroy(self, doThrow=True):
        if self._window:
            self._window.destroy()
            self._window = None
        self._is_open = False
        if self in YDialogGtk._open_dialogs:
            YDialogGtk._open_dialogs.remove(self)
        
        # Stop GTK main loop if no dialogs left
        if not YDialogGtk._open_dialogs:
            try:
                # Only quit the global Gtk main loop if it's actually running
                if hasattr(Gtk, "main_level") and Gtk.main_level() > 0:
                    Gtk.main_quit()
            except Exception:
                # be defensive: do not raise from cleanup
                pass
        return True

    def _post_event(self, event):
        """Internal: post an event to this dialog and quit local GLib.MainLoop if running."""
        self._event_result = event
        if self._glib_loop is not None and self._glib_loop.is_running():
            try:
                self._glib_loop.quit()
            except Exception:
                pass

    def waitForEvent(self, timeout_millisec=0):
        """
        Run a GLib.MainLoop until an event is posted or timeout occurs.
        Returns a YEvent (YWidgetEvent, YTimeoutEvent, ...).
        """
        # Ensure dialog is finalized/open (finalize if caller didn't call open()).
        if not self.isOpen():
            self.open()            

        # Let GTK process pending events (show/layout) before entering nested loop.
        while Gtk.events_pending():
            Gtk.main_iteration()

        self._event_result = None
        self._glib_loop = GLib.MainLoop()
 
        def on_timeout():
            # post timeout event and quit loop
            self._event_result = YTimeoutEvent()
            try:
                if self._glib_loop.is_running():
                    self._glib_loop.quit()
            except Exception:
                pass
            return False  # don't repeat

        self._timeout_id = None
        if timeout_millisec and timeout_millisec > 0:
            self._timeout_id = GLib.timeout_add(timeout_millisec, on_timeout)

        # run nested loop
        self._glib_loop.run()

        # cleanup
        if self._timeout_id:
            try:
                GLib.source_remove(self._timeout_id)
            except Exception:
                pass
            self._timeout_id = None
        self._glib_loop = None
        return self._event_result if self._event_result is not None else YEvent()

    @classmethod
    def deleteTopmostDialog(cls, doThrow=True):
        if cls._open_dialogs:
            dialog = cls._open_dialogs[-1]
            return dialog.destroy(doThrow)
        return False
    
    @classmethod
    def currentDialog(cls, doThrow=True):
        if not cls._open_dialogs:
            if doThrow:
                raise YUINoDialogException("No dialog open")
            return None
        return cls._open_dialogs[-1]
    
    def _create_backend_widget(self):
        self._window = Gtk.Window(title="YUI GTK Dialog")
        self._window.set_default_size(600, 400)
        self._window.set_border_width(10)
        
        if self._child:
            self._window.add(self._child.get_backend_widget())
        
        self._backend_widget = self._window
        # Connect to both "delete-event" (window manager close) and "destroy"
        # so we can post a YCancelEvent and stop any nested wait loop.
        self._window.connect("delete-event", self._on_delete_event)
        self._window.connect("destroy", self._on_destroy)
    
    def _on_destroy(self, widget):
        # normal widget destruction: ensure internal state cleaned
        try:
            # If no nested loop running, remove dialog and quit global loop if needed
            self.destroy()
        except Exception:
            pass

    def _on_delete_event(self, widget, event):
        # User clicked the window manager close (X) button:
        # post a YCancelEvent so waitForEvent can return YCancelEvent.
        try:
            self._post_event(YCancelEvent())
        except Exception:
            pass
        # Destroy the window and stop further handling
        try:
            self.destroy()
        except Exception:
            pass
        # Returning False allows the default handler to destroy the window;
        # we already destroyed it, so return False to continue.
        return False

class YVBoxGtk(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def widgetClass(self):
        return "YVBox"
    
    def _create_backend_widget(self):
        self._backend_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        for child in self._children:
            widget = child.get_backend_widget()
            expand = child.stretchable(YUIDimension.YD_VERT)
            fill = True
            padding = 0
            self._backend_widget.pack_start(widget, expand, fill, padding)

class YHBoxGtk(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def widgetClass(self):
        return "YHBox"
    
    def _create_backend_widget(self):
        self._backend_widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        for child in self._children:
            widget = child.get_backend_widget()
            expand = child.stretchable(YUIDimension.YD_HORIZ)
            fill = True
            padding = 0
            self._backend_widget.pack_start(widget, expand, fill, padding)

class YLabelGtk(YWidget):
    def __init__(self, parent=None, text="", isHeading=False, isOutputField=False):
        super().__init__(parent)
        self._text = text
        self._is_heading = isHeading
        self._is_output_field = isOutputField
    
    def widgetClass(self):
        return "YLabel"
    
    def text(self):
        return self._text
    
    def setText(self, new_text):
        self._text = new_text
        if self._backend_widget:
            self._backend_widget.set_text(new_text)
    
    def _create_backend_widget(self):
        self._backend_widget = Gtk.Label(label=self._text)
        self._backend_widget.set_xalign(0.0)  # Left align
        
        if self._is_heading:
            markup = f"<b>{self._text}</b>"
            self._backend_widget.set_markup(markup)

class YInputFieldGtk(YWidget):
    def __init__(self, parent=None, label="", password_mode=False):
        super().__init__(parent)
        self._label = label
        self._value = ""
        self._password_mode = password_mode
    
    def widgetClass(self):
        return "YInputField"
    
    def value(self):
        return self._value
    
    def setValue(self, text):
        self._value = text
        if hasattr(self, '_entry_widget') and self._entry_widget:
            self._entry_widget.set_text(text)
    
    def label(self):
        return self._label
    
    def _create_backend_widget(self):
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        if self._label:
            label = Gtk.Label(label=self._label)
            label.set_xalign(0.0)
            hbox.pack_start(label, False, False, 0)
        
        if self._password_mode:
            entry = Gtk.Entry()
            entry.set_visibility(False)
        else:
            entry = Gtk.Entry()
        
        entry.set_text(self._value)
        entry.connect("changed", self._on_changed)
        
        hbox.pack_start(entry, True, True, 0)
        self._backend_widget = hbox
        self._entry_widget = entry
    
    def _on_changed(self, entry):
        self._value = entry.get_text()

class YPushButtonGtk(YWidget):
    def __init__(self, parent=None, label=""):
        super().__init__(parent)
        self._label = label
    
    def widgetClass(self):
        return "YPushButton"
    
    def label(self):
        return self._label
    
    def setLabel(self, label):
        self._label = label
        if self._backend_widget:
            self._backend_widget.set_label(label)
    
    def _create_backend_widget(self):
        self._backend_widget = Gtk.Button(label=self._label)
        self._backend_widget.connect("clicked", self._on_clicked)
    
    def _on_clicked(self, button):
        # Post a YWidgetEvent to the containing dialog (walk parents)
        dlg = self.findDialog()
        if dlg is not None:
            dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
        else:
            print(f"Button clicked (no dialog found): {self._label}")

class YCheckBoxGtk(YWidget):
    def __init__(self, parent=None, label="", is_checked=False):
        super().__init__(parent)
        self._label = label
        self._is_checked = is_checked
    
    def widgetClass(self):
        return "YCheckBox"
    
    def value(self):
        return self._is_checked
    
    def setValue(self, checked):
        self._is_checked = checked
        if self._backend_widget:
            self._backend_widget.set_active(checked)
    
    def label(self):
        return self._label
    
    def _create_backend_widget(self):
        self._backend_widget = Gtk.CheckButton(label=self._label)
        self._backend_widget.set_active(self._is_checked)
        self._backend_widget.connect("toggled", self._on_toggled)
    
    def _on_toggled(self, button):
        self._is_checked = button.get_active()
        print(f"Checkbox toggled: {self._label} = {self._is_checked}")

class YComboBoxGtk(YSelectionWidget):
    def __init__(self, parent=None, label="", editable=False):
        super().__init__(parent)
        self._label = label
        self._editable = editable
        self._value = ""
        self._selected_items = []
    
    def widgetClass(self):
        return "YComboBox"
    
    def value(self):
        return self._value
    
    def setValue(self, text):
        # Always update internal value
        self._value = text
        # If backend combo already exists, update it immediately
        if hasattr(self, '_combo_widget') and self._combo_widget:
            try:
                if self._editable:
                    # For editable ComboBoxText with entry
                    entry = self._combo_widget.get_child()
                    if entry:
                        entry.set_text(text)
                else:
                    # Find and select the item
                    for i, item in enumerate(self._items):
                        if item.label() == text:
                            self._combo_widget.set_active(i)
                            break
                # Update selected_items to reflect new value
                self._selected_items = []
                for item in self._items:
                    if item.label() == text:
                        self._selected_items.append(item)
                        break
            except Exception:
                # be defensive if widget not fully initialized
                pass

    def editable(self):
        return self._editable
    
    def _create_backend_widget(self):
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        if self._label:
            label = Gtk.Label(label=self._label)
            label.set_xalign(0.0)
            hbox.pack_start(label, False, False, 0)

        if self._editable:
            # Create a ComboBoxText that is editable
            combo = Gtk.ComboBoxText.new_with_entry()
            entry = combo.get_child()
            if entry:
                entry.connect("changed", self._on_text_changed)
        else:
            combo = Gtk.ComboBoxText()
            combo.connect("changed", self._on_changed)

        # Add items to combo box
        for item in self._items:
            combo.append_text(item.label())

        # If a value was set prior to widget creation, apply it now
        if self._value:
            try:
                if self._editable:
                    entry = combo.get_child()
                    if entry:
                        entry.set_text(self._value)
                else:
                    for i, item in enumerate(self._items):
                        if item.label() == self._value:
                            combo.set_active(i)
                            break
                # update selected_items
                self._selected_items = []
                for item in self._items:
                    if item.label() == self._value:
                        self._selected_items.append(item)
                        break
            except Exception:
                pass

        hbox.pack_start(combo, True, True, 0)
        self._backend_widget = hbox
        self._combo_widget = combo

    def _on_text_changed(self, entry):
        # editable combo: update value and notify dialog
        try:
            text = entry.get_text()
        except Exception:
            text = ""
        self._value = text
        # update selected items (may be none for free text)
        self._selected_items = []
        for item in self._items:
            if item.label() == self._value:
                self._selected_items.append(item)
                break
        # Post selection-changed event
        try:
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
        except Exception:
            pass

    def _on_changed(self, combo):
        # non-editable combo: selection changed via index
        try:
            active_id = combo.get_active()
            if active_id >= 0:
                val = combo.get_active_text()
            else:
                val = ""
        except Exception:
            val = ""

        if val:
            self._value = val
            # Update selected items
            self._selected_items = []
            for item in self._items:
                if item.label() == self._value:
                    self._selected_items.append(item)
                    break
            # Post selection-changed event to containing dialog
            try:
                dlg = self.findDialog()
                if dlg is not None:
                    dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
            except Exception:
                pass
