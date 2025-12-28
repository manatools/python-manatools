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
from .backends.gtk import *

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
        self._product_name = "manatools AUI Gtk"
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
    
    def createMenuBar(self, parent):
        """Create a MenuBar widget (GTK backend)."""
        return YMenuBarGtk(parent)

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

    def createTable(self, parent, header: YTableHeader, multiSelection: bool = False):
        """Create a Table widget."""
        from .backends.gtk.tablegtk import YTableGtk
        return YTableGtk(parent, header, multiSelection)

    def createFrame(self, parent, label: str=""):
        """Create a Frame widget."""
        return YFrameGtk(parent, label)

    def createRichText(self, parent, text: str = "", plainTextMode: bool = False):
        """Create a RichText widget (GTK backend)."""
        from .backends.gtk.richtextgtk import YRichTextGtk
        return YRichTextGtk(parent, text, plainTextMode)

    def createCheckBoxFrame(self, parent, label: str = "", checked: bool = False):
        """Create a CheckBox Frame widget."""
        return YCheckBoxFrameGtk(parent, label, checked)

    def createProgressBar(self, parent, label, max_value=100):
        return YProgressBarGtk(parent, label, max_value)
    
    def createRadioButton(self, parent, label:str = "", isChecked:bool = False):    
        """Create a Radio Button widget."""
        return YRadioButtonGtk(parent, label, isChecked)
