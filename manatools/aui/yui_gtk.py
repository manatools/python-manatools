"""
GTK4 backend implementation for YUI (converted from GTK3)
"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, GObject, GdkPixbuf, GLib
import cairo
import threading
import os
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

    # Alignment helpers
    def createLeft(self, parent):
        return YAlignmentGtk(parent, horAlign=YAlignmentType.YAlignBegin,  vertAlign=YAlignmentType.YAlignUnchanged)

    def createRight(self, parent):
        return YAlignmentGtk(parent, horAlign=YAlignmentType.YAlignEnd, vertAlign=YAlignmentType.YAlignUnchanged)

    def createTop(self, parent):
        return YAlignmentGtk(parent, horAlign=YAlignmentType.YAlignUnchanged,   vertAlign=YAlignmentType.YAlignBegin)

    def createBottom(self, parent):
        return YAlignmentGtk(parent, horAlign=YAlignmentType.YAlignUnchanged,   vertAlign=YAlignmentType.YAlignEnd)

    def createHCenter(self, parent):
        return YAlignmentGtk(parent, horAlign=YAlignmentType.YAlignCenter, vertAlign=YAlignmentType.YAlignUnchanged)

    def createVCenter(self, parent):
        return YAlignmentGtk(parent, horAlign=YAlignmentType.YAlignUnchanged,      vertAlign=YAlignmentType.YAlignCenter)

    def createHVCenter(self, parent):
        return YAlignmentGtk(parent, horAlign=YAlignmentType.YAlignCenter, vertAlign=YAlignmentType.YAlignCenter)

    def createAlignment(self, parent, horAlignment: YAlignmentType, vertAlignment: YAlignmentType):
        """Create a generic YAlignment using YAlignmentType enums (or compatible specs)."""
        return YAlignmentGtk(parent, horAlign=horAlignment, vertAlign=vertAlignment)

    def createTree(self, parent, label, multiselection=False, recursiveselection = False):
        """Create a Tree widget."""
        return YTreeGtk(parent, label, multiselection, recursiveselection)

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

    def setVisible(self, visible):
        """Set widget visibility."""
        if self._backend_widget:
            try:
                self._backend_widget.set_visible(visible)
            except Exception:
                pass
        super().setVisible(visible)

    def _set_backend_enabled(self, enabled):
        """Enable/disable the dialog window backend."""
        try:
            if self._window is not None:
                try:
                    self._window.set_sensitive(enabled)
                except Exception:
                    # fallback: propagate to child content
                    try:
                        child = getattr(self, "_window", None)
                        if child and hasattr(child, "set_sensitive"):
                            child.set_sensitive(enabled)
                    except Exception:
                        pass
        except Exception:
            pass


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

    def _set_backend_enabled(self, enabled):
        """Enable/disable the VBox and propagate to children."""
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass
        # propagate logical enabled state to child widgets so they update their backends
        try:
            for c in list(getattr(self, "_children", []) or []):
                try:
                    c.setEnabled(enabled)
                except Exception:
                    pass
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
            print("HBox child: ", child.widgetClass())
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

    def _set_backend_enabled(self, enabled):
        """Enable/disable the HBox and propagate to children."""
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            for c in list(getattr(self, "_children", []) or []):
                try:
                    c.setEnabled(enabled)
                except Exception:
                    pass
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

    def _set_backend_enabled(self, enabled):
        """Enable/disable the label widget backend."""
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    pass
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

    def _set_backend_enabled(self, enabled):
        """Enable/disable the input field (entry and container)."""
        try:
            if getattr(self, "_entry_widget", None) is not None:
                try:
                    self._entry_widget.set_sensitive(enabled)
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

    def _set_backend_enabled(self, enabled):
        """Enable/disable the push button backend."""
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
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

    def _set_backend_enabled(self, enabled):
        """Enable/disable the check button backend."""
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass

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


class YAlignmentGtk(YSingleChildContainerWidget):
    """
    GTK4 implementation of YAlignment.

    - Uses a Gtk.Box as a lightweight container that requests expansion when
      needed so child halign/valign can take effect (matches the small GTK sample).
    - Applies halign/valign hints to the child's backend widget.
    - Defers attaching the child if its backend is not yet created (GLib.idle_add).
    - Supports an optional repeating background pixbuf painted in the draw signal.
    """
    def __init__(self, parent=None, horAlign: YAlignmentType=YAlignmentType.YAlignUnchanged, vertAlign: YAlignmentType=YAlignmentType.YAlignUnchanged):
        super().__init__(parent)
        self._halign_spec = horAlign
        self._valign_spec = vertAlign
        self._background_pixbuf = None
        self._signal_id = None
        self._backend_widget = None
        # schedule guard for deferred attach
        self._attach_scheduled = False
        # Track if we've already attached a child
        self._child_attached = False

    def widgetClass(self):
        return "YAlignment"

    def _to_gtk_halign(self):
        """Convert Horizontal YAlignmentType to Gtk.Align or None."""        
        if self._halign_spec:
            if self._halign_spec == YAlignmentType.YAlignBegin:
                return Gtk.Align.START
            if self._halign_spec == YAlignmentType.YAlignCenter:
                return Gtk.Align.CENTER
            if self._halign_spec == YAlignmentType.YAlignEnd:
                return Gtk.Align.END
        return None
    
    def _to_gtk_valign(self):
        """Convert Vertical YAlignmentType to Gtk.Align or None."""        
        if self._valign_spec:
            if self._valign_spec == YAlignmentType.YAlignBegin:
                return Gtk.Align.START
            if self._valign_spec == YAlignmentType.YAlignCenter:
                return Gtk.Align.CENTER
            if self._valign_spec == YAlignmentType.YAlignEnd:
                return Gtk.Align.END
        return None

    #def stretchable(self, dim):
    #    """Report whether this alignment should expand in given dimension.
    #
    #    Parents (HBox/VBox) use this to distribute space.
    #    """
    #    try:
    #        if dim == YUIDimension.YD_HORIZ:
    #            align = self._to_gtk_halign()
    #            return align in (Gtk.Align.CENTER, Gtk.Align.END) #TODO: verify
    #        if dim == YUIDimension.YD_VERT:
    #            align = self._to_gtk_valign()
    #            return align == Gtk.Align.CENTER #TODO: verify
    #    except Exception:
    #        pass
    #    return False

    def stretchable(self, dim: YUIDimension):
        ''' Returns the stretchability of the layout box:
          * The layout box is stretchable if the child is stretchable in
          * this dimension or if the child widget has a layout weight in
          * this dimension.
        '''
        if self._child:
            expand = bool(self._child.stretchable(dim))
            weight = bool(self._child.weight(dim))
            if expand or weight:
                return True
        return False

    def setBackgroundPixmap(self, filename):
        """Set a repeating background pixbuf and connect draw handler."""
        # disconnect previous handler
        if self._signal_id and self._backend_widget:
            try:
                self._backend_widget.disconnect(self._signal_id)
            except Exception:
                pass
            self._signal_id = None

        # release previous pixbuf if present
        self._background_pixbuf = None

        if filename:
            try:
                self._background_pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
                if self._backend_widget:
                    self._signal_id = self._backend_widget.connect("draw", self._on_draw)
                    self._backend_widget.queue_draw()  # Trigger redraw
            except Exception as e:
                print(f"Failed to load background image: {e}")
                self._background_pixbuf = None

    def _on_draw(self, widget, cr):
        """Draw callback that tiles the background pixbuf."""
        if not self._background_pixbuf:
            return False
        try:
            # Get actual allocation
            width = widget.get_allocated_width()
            height = widget.get_allocated_height()
            
            Gdk.cairo_set_source_pixbuf(cr, self._background_pixbuf, 0, 0)
            # set repeat
            pat = cr.get_source()
            pat.set_extend(cairo.Extend.REPEAT)
            cr.rectangle(0, 0, width, height)
            cr.fill()
        except Exception as e:
            print(f"Error drawing background: {e}")
        return False

    def addChild(self, child):
        """Keep base behavior and ensure we attempt to attach child's backend."""
        try:
            super().addChild(child)
        except Exception:
            self._child = child
        self._child_attached = False
        self._schedule_attach_child()

    def setChild(self, child):
        """Keep base behavior and ensure we attempt to attach child's backend."""
        try:
            super().setChild(child)
        except Exception:
            self._child = child
        self._child_attached = False
        self._schedule_attach_child()

    def _schedule_attach_child(self):
        """Schedule a single idle callback to attach child backend later."""
        if self._attach_scheduled or self._child_attached:
            return
        self._attach_scheduled = True

        def _idle_cb():
            self._attach_scheduled = False
            try:
                self._ensure_child_attached()
            except Exception as e:
                print(f"Error attaching child: {e}")
            return False

        try:
            GLib.idle_add(_idle_cb)
        except Exception:
            # fallback: call synchronously if idle_add not available
            _idle_cb()

    def _ensure_child_attached(self):
        """Attach child's backend to our container, apply alignment hints."""
        if self._backend_widget is None:
            self._create_backend_widget()
            return

        # choose child reference (support _child or _children storage)
        child = getattr(self, "_child", None)
        if child is None:
            try:
                chs = getattr(self, "_children", None) or []
                child = chs[0] if chs else None
            except Exception:
                child = None
        if child is None:
            return

        # get child's backend widget
        try:
            cw = child.get_backend_widget()
        except Exception:
            cw = None

        if cw is None:
            # child backend not yet ready; schedule again
            if not self._child_attached:
                self._schedule_attach_child()
            return

        # convert specs -> Gtk.Align
        hal = self._to_gtk_halign()
        val = self._to_gtk_valign()

        # Apply alignment and expansion hints to child
        try:
            # Set horizontal alignment and expansion
            if hasattr(cw, "set_halign"):
                if hal is not None:
                    cw.set_halign(hal)
                else:
                    cw.set_halign(Gtk.Align.FILL)
                
                # Request expansion for alignment to work properly
                cw.set_hexpand(True)
            
            # Set vertical alignment and expansion  
            if hasattr(cw, "set_valign"):
                if val is not None:
                    cw.set_valign(val)
                else:
                    cw.set_valign(Gtk.Align.FILL)
                
                # Request expansion for alignment to work properly
                cw.set_vexpand(True)
                
        except Exception as e:
            print(f"Error setting alignment properties: {e}")

        # If the child widget is already parented to us, nothing to do
        parent_of_cw = None
        try:
            if hasattr(cw, 'get_parent'):
                parent_of_cw = cw.get_parent()
        except Exception:
            parent_of_cw = None

        if parent_of_cw == self._backend_widget:
            self._child_attached = True
            return

        # Remove any existing children from our container
        try:
            # In GTK4, we need to remove all existing children
            while True:
                child_widget = self._backend_widget.get_first_child()
                if child_widget is None:
                    break
                self._backend_widget.remove(child_widget)
        except Exception as e:
            print(f"Error removing existing children: {e}")

        # Append child to our box - this is the critical fix for GTK4
        try:
            self._backend_widget.append(cw)
            self._child_attached = True
            print(f"Successfully attached child {child.widgetClass()} {child.debugLabel()} to alignment container")
        except Exception as e:
            print(f"Error appending child: {e}")
            # Try alternative method for GTK4
            try:
                self._backend_widget.set_child(cw)
                self._child_attached = True
                print(f"Successfully set child {child.widgetClass()} {child.debugLabel()} using set_child()")
            except Exception as e2:
                print(f"Error setting child: {e2}")

    def _create_backend_widget(self):
        """Create a Box container oriented to allow alignment to work.

        In GTK4, we use a simple Box that expands in both directions
        to provide space for the child widget to align within.
        """
        try:
            # Use a box that can expand in both directions
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            
            # Make the box expand to fill available space
            box.set_hexpand(True)
            box.set_vexpand(True)
            
            # Set the box to fill its allocation so child has space to align
            box.set_halign(Gtk.Align.FILL)
            box.set_valign(Gtk.Align.FILL)
            
        except Exception as e:
            print(f"Error creating backend widget: {e}")
            box = Gtk.Box()

        self._backend_widget = box

        # Connect draw handler if we have a background pixbuf
        if self._background_pixbuf and not self._signal_id:
            try:
                self._signal_id = box.connect("draw", self._on_draw)
            except Exception as e:
                print(f"Error connecting draw signal: {e}")
                self._signal_id = None

        # Mark that backend is ready and attempt to attach child
        self._ensure_child_attached()

    def get_backend_widget(self):
        """Return the backend GTK widget."""
        if self._backend_widget is None:
            self._create_backend_widget()
        return self._backend_widget

    def setSize(self, width, height):
        """Set size of the alignment widget."""
        if self._backend_widget:
            if width > 0 and height > 0:
                self._backend_widget.set_size_request(width, height)
            else:
                self._backend_widget.set_size_request(-1, -1)

    def setEnabled(self, enabled):
        """Set widget enabled state."""
        if self._backend_widget:
            self._backend_widget.set_sensitive(enabled)
        super().setEnabled(enabled)

    def setVisible(self, visible):
        """Set widget visibility."""
        if self._backend_widget:
            try:
                self._backend_widget.set_visible(visible)
            except Exception:
                pass
        super().setVisible(visible)

    def _set_backend_enabled(self, enabled):
        """Enable/disable the alignment container and its child (if any)."""
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass
        # propagate to logical child so child's backend updates too
        try:
            child = getattr(self, "_child", None)
            if child is None:
                chs = getattr(self, "_children", None) or []
                child = chs[0] if chs else None
            if child is not None:
                try:
                    child.setEnabled(enabled)
                except Exception:
                    pass
        except Exception:
            pass

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
            listbox.set_vexpand(True)
            listbox.set_hexpand(True)
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
            sw.set_vexpand(True)
            sw.set_hexpand(True)
            vbox.set_vexpand(True)
            vbox.set_hexpand(True)
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
                btn.set_focus_on_click(False)
                btn.connect("clicked", lambda b, it=item: self._on_toggle_clicked(it))
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
            cur = bool(getattr(item, "_is_open", False))
            try:
                item._is_open = not cur
            except Exception:
                try:
                    item.setOpen(not cur)
                except Exception:
                    pass
            # preserve selection ids
            try:
                self._last_selected_ids = set(id(i) for i in self._selected_items)
            except Exception:
                self._last_selected_ids = set()
            self.rebuildTree()
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
            # clear listbox rows
            try:
                for r in list(self._listbox.get_children()):
                    try:
                        self._listbox.remove(r)
                    except Exception:
                        try:
                            self._listbox.unbind_model()
                        except Exception:
                            pass
            except Exception:
                # fallback ignore
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

    def _on_row_selected(self, listbox, row):
        """Handle selection change; implement recursive selection propagation."""
        if self._suppress_selection_handler:
            return
        try:
            # collect currently selected items (by id)
            cur_selected_ids = set()
            selected_rows = []
            try:
                # prefer scanning rows API
                for r in self._rows:
                    try:
                        sel = False
                        if getattr(r, "get_selected", None):
                            sel = r.get_selected()
                        else:
                            sel = bool(getattr(r, "_selected_flag", False))
                        if sel:
                            selected_rows.append(r)
                            it = self._row_to_item.get(r, None)
                            if it is not None:
                                cur_selected_ids.add(id(it))
                    except Exception:
                        pass
            except Exception:
                pass

            added = cur_selected_ids - self._last_selected_ids
            removed = self._last_selected_ids - cur_selected_ids

            # Recursive + multi: selecting parent selects all descendants; deselecting parent deselects descendants
            if self._recursive and self._multi:
                desired_ids = set(cur_selected_ids)
                # handle added -> add descendants
                for r in list(selected_rows):
                    try:
                        it = self._row_to_item.get(r, None)
                        if it is None:
                            continue
                        if id(it) in added:
                            for d in self._collect_all_descendants(it):
                                desired_ids.add(id(d))
                    except Exception:
                        pass
                # handle removed -> remove descendants
                for rid in list(removed):
                    try:
                        # find item object by id among previous items (we can search self._items tree)
                        def _find_by_id(target_id, nodes):
                            for n in nodes:
                                if id(n) == target_id:
                                    return n
                                try:
                                    chs = []
                                    if callable(getattr(n, "children", None)):
                                        chs = n.children() or []
                                    else:
                                        chs = getattr(n, "_children", []) or []
                                except Exception:
                                    chs = getattr(n, "_children", []) or []
                                res = _find_by_id(target_id, chs)
                                if res:
                                    return res
                            return None
                        obj = _find_by_id(rid, list(getattr(self, "_items", []) or []))
                        if obj is not None:
                            for d in self._collect_all_descendants(obj):
                                if id(d) in desired_ids:
                                    desired_ids.discard(id(d))
                    except Exception:
                        pass

                # apply desired_ids to visible rows
                if desired_ids != cur_selected_ids:
                    try:
                        self._suppress_selection_handler = True
                        try:
                            self._listbox.unselect_all()
                        except Exception:
                            pass
                        for row, it in list(self._row_to_item.items()):
                            try:
                                if id(it) in desired_ids:
                                    try:
                                        row.set_selected(True)
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                    finally:
                        self._suppress_selection_handler = False

                    # recompute selection sets after applying
                    cur_selected_ids = set()
                    try:
                        for r in self._rows:
                            try:
                                sel = False
                                if getattr(r, "get_selected", None):
                                    sel = r.get_selected()
                                else:
                                    sel = bool(getattr(r, "_selected_flag", False))
                                if sel:
                                    it = self._row_to_item.get(r, None)
                                    if it is not None:
                                        cur_selected_ids.add(id(it))
                            except Exception:
                                pass
                    except Exception:
                        pass

            # Build logical selection list and set YItem selected flags
            new_selected = []
            try:
                # clear previous selection flags on all items
                def _clear_flags(nodes):
                    for n in nodes:
                        try:
                            n.setSelected(False)
                        except Exception:
                            pass
                        try:
                            childs = []
                            if callable(getattr(n, "children", None)):
                                childs = n.children() or []
                            else:
                                childs = getattr(n, "_children", []) or []
                        except Exception:
                            childs = getattr(n, "_children", []) or []
                        if childs:
                            _clear_flags(childs)
                _clear_flags(list(getattr(self, "_items", []) or []))
            except Exception:
                pass

            for r in self._rows:
                try:
                    sel = False
                    if getattr(r, "get_selected", None):
                        sel = r.get_selected()
                    else:
                        sel = bool(getattr(r, "_selected_flag", False))
                    if sel:
                        it = self._row_to_item.get(r, None)
                        if it is not None:
                            try:
                                it.setSelected(True)
                            except Exception:
                                pass
                            new_selected.append(it)
                except Exception:
                    pass

            self._selected_items = new_selected
            self._last_selected_ids = set(id(i) for i in self._selected_items)

            if self._immediate and self.notify():
                dlg = self.findDialog()
                if dlg:
                    dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
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

    def immediateMode(self):
        return bool(self._immediate)

    def setImmediateMode(self, on=True):
        self._immediate = bool(on)

    def hasMultiSelection(self):
        return bool(self._multi)

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
