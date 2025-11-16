"""
GTK4 backend implementation for YUI (converted from GTK3)
"""
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
import threading
import os
try:
    from gi.repository import GdkPixbuf
except Exception:
    GdkPixbuf = None
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
        self._application_title = "manatools GTK Application"
        self._product_name = "manatools YUI GTK"
        self._icon_base_path = None
        self._icon = ""
        # cached resolved GdkPixbuf.Pixbuf (or None)
        self._gtk_icon_pixbuf = None

    def _resolve_pixbuf(self, icon_spec):
        """Resolve icon_spec into a GdkPixbuf.Pixbuf if possible.
        Prefer local path resolved against iconBasePath if set, else try theme lookup.
        """
        if not icon_spec:
            return None
        # try explicit path (icon_base_path forced)
        try:
            # if base path set and icon_spec not absolute, try join
            if self._icon_base_path:
                cand = icon_spec if os.path.isabs(icon_spec) else os.path.join(self._icon_base_path, icon_spec)
                if os.path.exists(cand) and GdkPixbuf is not None:
                    try:
                        return GdkPixbuf.Pixbuf.new_from_file(cand)
                    except Exception:
                        pass
            # try absolute path
            if os.path.isabs(icon_spec) and os.path.exists(icon_spec) and GdkPixbuf is not None:
                try:
                    return GdkPixbuf.Pixbuf.new_from_file(icon_spec)
                except Exception:
                    pass
        except Exception:
            pass

        # fallback: try icon theme lookup
        try:
            theme = Gtk.IconTheme.get_default()
            # request a reasonable size (48) - theme will scale as needed
            if theme and theme.has_icon(icon_spec) and GdkPixbuf is not None:
                try:
                    pix = theme.load_icon(icon_spec, 48, 0)
                    if pix is not None:
                        return pix
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def iconBasePath(self):
        return self._icon_base_path
    
    def setIconBasePath(self, new_icon_base_path):
        self._icon_base_path = new_icon_base_path
    
    def setProductName(self, product_name):
        self._product_name = product_name
    
    def productName(self):
        return self._product_name
    
    def setApplicationTitle(self, title):
        """Set the application title and try to update dialogs/windows."""
        self._application_title = title
        try:
            # update the top most YDialogGtk window if available
            try:
                dlg = YDialogGtk.currentDialog(doThrow=False)
                if dlg:
                    win = getattr(dlg, "_window", None)
                    if win:
                        try:
                            win.set_title(title)
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            pass

    def applicationTitle(self):
        """Get the application title."""
        return self._application_title
    
    def setApplicationIcon(self, Icon):
        """Set application icon spec (theme name or path). If iconBasePath is set, prefer local file."""
        try:
            self._icon = Icon or ""
        except Exception:
            self._icon = ""
        # resolve and cache a GdkPixbuf if possible
        try:
            self._gtk_icon_pixbuf = self._resolve_pixbuf(self._icon)
        except Exception:
            self._gtk_icon_pixbuf = None

        # Try to set a global default icon for windows (best-effort)
        try:
            if self._gtk_icon_pixbuf is not None:
                # Gtk.Window.set_default_icon/from_file may be available
                try:
                    Gtk.Window.set_default_icon(self._gtk_icon_pixbuf)
                except Exception:
                    try:
                        # try using file path if we resolved one from disk
                        if self._icon_base_path:
                            cand = self._icon if os.path.isabs(self._icon) else os.path.join(self._icon_base_path, self._icon)
                            if os.path.exists(cand):
                                Gtk.Window.set_default_icon_from_file(cand)
                        else:
                            # if _icon was an absolute file
                            if os.path.isabs(self._icon) and os.path.exists(self._icon):
                                Gtk.Window.set_default_icon_from_file(self._icon)
                    except Exception:
                        pass
        except Exception:
            pass

        # Apply icon to any open YDialogGtk windows
        try:
            for dlg in getattr(YDialogGtk, "_open_dialogs", []) or []:
                try:
                    win = getattr(dlg, "_window", None)
                    if win:
                        if self._gtk_icon_pixbuf is not None:
                            try:
                                # try direct pixbuf assignment
                                win.set_icon(self._gtk_icon_pixbuf)
                            except Exception:
                                try:
                                    # try setting icon name as fallback
                                    win.set_icon_name(self._icon)
                                except Exception:
                                    pass
                        else:
                            # if we have only a name, try icon name
                            try:
                                win.set_icon_name(self._icon)
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            pass
    
    def applicationIcon(self):
        return self._icon


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
    
    def createSelectionBox(self, parent, label):
        return YSelectionBoxGtk(parent, label)


# GTK4 Widget Implementations
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
    
    @staticmethod
    def currentDialog(doThrow=True):
        open_dialog = YDialogGtk._open_dialogs[-1] if YDialogGtk._open_dialogs else None
        if not open_dialog and doThrow:
            raise YUINoDialogException("No dialog is currently open")
        return open_dialog

    @staticmethod
    def topmostDialog(doThrow=True):
        ''' same as currentDialog '''
        return YDialogGtk.currentDialog(doThrow=doThrow)
    
    def isTopmostDialog(self):
        '''Return whether this dialog is the topmost open dialog.'''
        return YDialogGtk._open_dialogs[-1] == self if YDialogGtk._open_dialogs else False

    def open(self):
        # Finalize and show the dialog in a non-blocking way.
        if not self._is_open:
            if not self._window:
                self._create_backend_widget()
            # in Gtk4, show_all is not recommended; use present() or show
            try:
                self._window.present()
            except Exception:
                try:
                    self._window.show()
                except Exception:
                    pass
            self._is_open = True
    
    def isOpen(self):
        return self._is_open
    
    def destroy(self, doThrow=True):
        if self._window:
            try:
                self._window.destroy()
            except Exception:
                try:
                    self._window.close()
                except Exception:
                    pass
            self._window = None
        self._is_open = False
        if self in YDialogGtk._open_dialogs:
            YDialogGtk._open_dialogs.remove(self)
        
        # Stop GLib main loop if no dialogs left (nested loops only)
        if not YDialogGtk._open_dialogs:
            try:
                if self._glib_loop and self._glib_loop.is_running():
                    self._glib_loop.quit()
            except Exception:
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

        # Let GTK/GLib process pending events (show/layout) before entering nested loop.
        # Gtk.events_pending()/Gtk.main_iteration() do not exist in GTK4; use MainContext iteration.
        try:
            ctx = GLib.MainContext.default()
            while ctx.pending():
                ctx.iteration(False)
        except Exception:
            # be defensive if API differs on some bindings
            pass

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
        # Determine window title from YApplicationGtk instance stored on the YUI backend
        title = "Manatools YUI GTK Dialog"
        try:
            from . import yui as yui_mod
            appobj = None
            # YUI._backend may hold the backend instance (YUIGtk)
            backend = getattr(yui_mod.YUI, "_backend", None)
            if backend and hasattr(backend, "application"):
                appobj = backend.application()
            # fallback: YUI._instance might be set and expose application/yApp
            if not appobj:
                inst = getattr(yui_mod.YUI, "_instance", None)
                if inst and hasattr(inst, "application"):
                    appobj = inst.application()
            if appobj and hasattr(appobj, "applicationTitle"):
                atitle = appobj.applicationTitle()
                if atitle:
                    title = atitle
            # try to obtain resolved pixbuf from application and store for window icon
            _resolved_pixbuf = None
            try:
                _resolved_pixbuf = getattr(appobj, "_gtk_icon_pixbuf", None)
            except Exception:
                _resolved_pixbuf = None
        except Exception:
            pass

        # Create Gtk4 Window
        self._window = Gtk.Window(title=title)
        # set window icon if available
        try:
            if _resolved_pixbuf is not None:
                try:
                    self._window.set_icon(_resolved_pixbuf)
                except Exception:
                    try:
                        # fallback to name if pixbuf not accepted
                        icname = getattr(appobj, "applicationIcon", lambda : None)()
                        if icname:
                            self._window.set_icon_name(icname)
                    except Exception:
                        pass
            else:
                try:
                    # try setting icon name if application provided it
                    icname = getattr(appobj, "applicationIcon", lambda : None)()
                    if icname:
                        self._window.set_icon_name(icname)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self._window.set_default_size(600, 400)
        except Exception:
            pass

        # Content container with margins (window.set_child used in Gtk4)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        content.set_margin_start(10)
        content.set_margin_end(10)
        content.set_margin_top(10)
        content.set_margin_bottom(10)

        if self._child:
            child_widget = self._child.get_backend_widget()
            # ensure child is shown properly
            try:
                content.append(child_widget)
            except Exception:
                try:
                    content.add(child_widget)
                except Exception:
                    pass

        try:
            self._window.set_child(content)
        except Exception:
            # fallback for older bindings
            try:
                self._window.add(content)
            except Exception:
                pass

        self._backend_widget = self._window
        # Connect destroy/close handlers
        try:
            # Gtk4: use 'close-request' if available, otherwise 'destroy'
            if hasattr(self._window, "connect"):
                try:
                    self._window.connect("close-request", self._on_delete_event)
                except Exception:
                    try:
                        self._window.connect("destroy", self._on_destroy)
                    except Exception:
                        pass
        except Exception:
            pass
    
    def _on_destroy(self, widget):
        try:
            self.destroy()
        except Exception:
            pass

    def _on_delete_event(self, *args):
        # close-request handler in Gtk4: post cancel event and destroy
        try:
            self._post_event(YCancelEvent())
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
        # returning False/True not used in this simplified handler
        return False


class YVBoxGtk(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def widgetClass(self):
        return "YVBox"
    
    # Returns the stretchability of the layout box:
    def stretchable(self, dim):
        for child in self._children:
            expand = bool(child.stretchable(dim))
            weight = bool(child.weight(dim))
            if expand or weight:
                return True
        return False

    def _create_backend_widget(self):
        self._backend_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        for child in self._children:
            widget = child.get_backend_widget()
            expand = bool(child.stretchable(YUIDimension.YD_VERT))
            fill = True
            padding = 0

            try:
                if expand:
                    if hasattr(widget, "set_vexpand"):
                        widget.set_vexpand(True)
                    if hasattr(widget, "set_valign"):
                        widget.set_valign(Gtk.Align.FILL)
                    if hasattr(widget, "set_hexpand"):
                        widget.set_hexpand(True)
                    if hasattr(widget, "set_halign"):
                        widget.set_halign(Gtk.Align.FILL)
                else:
                    if hasattr(widget, "set_vexpand"):
                        widget.set_vexpand(False)
                    if hasattr(widget, "set_valign"):
                        widget.set_valign(Gtk.Align.START)
                    if hasattr(widget, "set_hexpand"):
                        widget.set_hexpand(False)
                    if hasattr(widget, "set_halign"):
                        widget.set_halign(Gtk.Align.START)
            except Exception:
                pass

            # Gtk4: use append instead of pack_start
            try:
                self._backend_widget.append(widget)
            except Exception:
                try:
                    self._backend_widget.add(widget)
                except Exception:
                    pass

class YHBoxGtk(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def widgetClass(self):
        return "YHBox"

    def stretchable(self, dim):
        for child in self._children:
            expand = bool(child.stretchable(dim))
            weight = bool(child.weight(dim))
            if expand or weight:
                return True
        return False

    def _create_backend_widget(self):
        self._backend_widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        for child in self._children:
            widget = child.get_backend_widget()
            expand = bool(child.stretchable(YUIDimension.YD_HORIZ))
            fill = True
            padding = 0
            try:
                if expand:
                    if hasattr(widget, "set_hexpand"):
                        widget.set_hexpand(True)
                    if hasattr(widget, "set_halign"):
                        widget.set_halign(Gtk.Align.FILL)
                else:
                    if hasattr(widget, "set_hexpand"):
                        widget.set_hexpand(False)
                    if hasattr(widget, "set_halign"):
                        widget.set_halign(Gtk.Align.START)
            except Exception:
                pass

            try:
                self._backend_widget.append(widget)
            except Exception:
                try:
                    self._backend_widget.add(widget)
                except Exception:
                    pass

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
            try:
                self._backend_widget.set_text(new_text)
            except Exception:
                pass
    
    def _create_backend_widget(self):
        self._backend_widget = Gtk.Label(label=self._text)
        try:
            # alignment API in Gtk4 differs; fall back to setting xalign if available
            if hasattr(self._backend_widget, "set_xalign"):
                self._backend_widget.set_xalign(0.0)
        except Exception:
            pass
        
        if self._is_heading:
            try:
                markup = f"<b>{self._text}</b>"
                self._backend_widget.set_markup(markup)
            except Exception:
                pass

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
            try:
                self._entry_widget.set_text(text)
            except Exception:
                pass
    
    def label(self):
        return self._label
    
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
        
        if self._password_mode:
            entry = Gtk.Entry()
            try:
                entry.set_visibility(False)
            except Exception:
                pass
        else:
            entry = Gtk.Entry()
        
        try:
            entry.set_text(self._value)
            entry.connect("changed", self._on_changed)
        except Exception:
            pass
        
        try:
            hbox.append(entry)
        except Exception:
            hbox.add(entry)

        self._backend_widget = hbox
        self._entry_widget = entry
    
    def _on_changed(self, entry):
        try:
            self._value = entry.get_text()
        except Exception:
            self._value = ""

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
            try:
                self._backend_widget.set_label(label)
            except Exception:
                pass
    
    def _create_backend_widget(self):
        self._backend_widget = Gtk.Button(label=self._label)
        # Prevent button from being stretched horizontally by default.
        try:
            if hasattr(self._backend_widget, "set_hexpand"):
                self._backend_widget.set_hexpand(False)
            if hasattr(self._backend_widget, "set_halign"):
                self._backend_widget.set_halign(Gtk.Align.START)
        except Exception:
            pass
        try:
            self._backend_widget.connect("clicked", self._on_clicked)
        except Exception:
            pass
    
    def _on_clicked(self, button):
        if self.notify() is False:
            return
        dlg = self.findDialog()
        if dlg is not None:
            dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
        else:
            # silent fallback
            pass

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
            try:
                self._backend_widget.set_active(checked)
            except Exception:
                pass
    
    def label(self):
        return self._label
    
    def _create_backend_widget(self):
        self._backend_widget = Gtk.CheckButton(label=self._label)
        try:
            self._backend_widget.set_active(self._is_checked)
            self._backend_widget.connect("toggled", self._on_toggled)
        except Exception:
            pass
    
    def _on_toggled(self, button):
        try:
            self._is_checked = button.get_active()
        except Exception:
            self._is_checked = bool(self._is_checked)
        
        if self.notify():
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))

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
        # notify
        self._on_selection_changed()

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
        self._on_selection_changed()

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
            if row is not None:
                if self._multi_selection:
                    # toggle selection state for this row
                    try:
                        cur = self._row_is_selected(row)
                        try:
                            row.set_selected(not cur)
                        except Exception:
                            # fallback: store a flag when set_selected isn't available
                            setattr(row, "_selected_flag", not cur)
                    except Exception:
                        pass
                else:
                    # single-selection: select provided row and deselect others
                    for r in getattr(self, "_rows", []):
                        try:
                            r.set_selected(r is row)
                        except Exception:
                            try:
                                setattr(r, "_selected_flag", (r is row))
                            except Exception:
                                pass

            # rebuild selected_items scanning cached rows (works for both modes)
            self._selected_items = []
            for i, r in enumerate(getattr(self, "_rows", [])):
                try:
                    if self._row_is_selected(r) and i < len(self._items):
                        self._selected_items.append(self._items[i])
                except Exception:
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
