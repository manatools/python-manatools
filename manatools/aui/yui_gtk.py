"""
GTK4 backend implementation for YUI (converted from GTK3)
"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, GObject, GdkPixbuf, GLib, Gio
from typing import List
import os
import logging
from .yui_common import *
from .backends.gtk import *


class YUIGtk:
    def __init__(self):
        # Use a dedicated widget factory to match other backends.
        self._widget_factory = YWidgetFactoryGtk()
        self._optional_widget_factory = None
        self._application = YApplicationGtk()
        try:
            self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        except Exception:
            self._logger = logging.getLogger("manatools.aui.gtk.YUIGtk")
    
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
        self._icon = "manatools"  # default icon name
        # cached resolved GdkPixbuf.Pixbuf (or None)
        self._gtk_icon_pixbuf = None
        try:
            self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        except Exception:
            self._logger = logging.getLogger("manatools.aui.gtk.YApplicationGtk")

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

    def _create_gtk4_filters(self, filter_str: str) -> List[Gtk.FileFilter]:
        """
        Create GTK4 file filters from a semicolon-separated filter string.
        """
        filters = []
        
        if not filter_str or filter_str.strip() == "":
            return filters
        
        # Split and clean patterns
        patterns = [p.strip() for p in filter_str.split(';') if p.strip()]
        
        # Create main filter
        main_filter = Gtk.FileFilter()
        
        # Set a meaningful name
        if len(patterns) == 1:
            ext = patterns[0].replace('*.', '').replace('*', '')
            main_filter.set_name(f"{ext.upper()} files")
        else:
            main_filter.set_name("Supported files")
        
        # Add patterns to the filter
        for pattern in patterns:
            pattern = pattern.strip()
            if not pattern:
                continue
                
            # Handle different pattern formats
            if pattern == "*" or pattern == "*.*":
                # All files
                main_filter.add_pattern("*")
            elif pattern.startswith("*."):
                # Pattern like "*.txt"
                main_filter.add_pattern(pattern)
                # Also add without star for some systems
                main_filter.add_pattern(pattern[1:])  # ".txt"
            elif pattern.startswith("."):
                # Pattern like ".txt"
                main_filter.add_pattern(f"*{pattern}")  # "*.txt"
                main_filter.add_pattern(pattern)        # ".txt"
            else:
                # Try as mime type or literal pattern
                if '/' in pattern:  # Looks like a mime type
                    main_filter.add_mime_type(pattern)
                else:
                    main_filter.add_pattern(pattern)
        
        filters.append(main_filter)
        
        # Add "All files" filter
        all_filter = Gtk.FileFilter()
        all_filter.set_name("All files")
        all_filter.add_pattern("*")
        filters.append(all_filter)
        
        return filters

    def askForExistingDirectory(self, startDir: str, headline: str):
        """
        Prompt user to select an existing directory (GTK implementation).
        """
        try:
            # try to find an active YDialogGtk window to use as transient parent
            parent_window = None
            try:
                for od in getattr(YDialogGtk, "_open_dialogs", []) or []:
                    try:
                        w = getattr(od, "_window", None)
                        if w:
                            parent_window = w
                            break
                    except Exception:
                        pass
            except Exception:
                parent_window = None

            # ensure application name is set so recent manager can record resources
            try:
                GLib.set_prgname(self._product_name or "manatools")
            except Exception:
                pass
            # Log portal-related environment to help diagnose behavior differences
            try:
                self._logger.debug("GTK_USE_PORTAL=%s", os.environ.get("GTK_USE_PORTAL"))
                self._logger.debug("XDG_CURRENT_DESKTOP=%s", os.environ.get("XDG_CURRENT_DESKTOP"))
            except Exception:
                pass

            # Use Gtk.FileDialog (GTK 4.10+) exclusively for directory selection
            if not hasattr(Gtk, 'FileDialog'):
                try:
                    self._logger.error('Gtk.FileDialog is not available in this GTK runtime')
                except Exception:
                    pass
                return ""

            try:
                fd = Gtk.FileDialog.new()
                try:
                    fd.set_title(headline or "Select Directory")
                except Exception:
                    pass

                try:
                    fd.set_modal(True)
                except Exception:
                    pass

                if startDir and os.path.exists(startDir):
                    try:
                        fd.set_initial_folder(Gio.File.new_for_path(startDir))
                    except Exception:
                        try:
                            fd.set_initial_folder_uri(GLib.filename_to_uri(startDir, None))
                        except Exception:
                            pass

                loop = GLib.MainLoop()
                result_holder = {'file': None}

                def _on_opened(dialog, result, _lh=loop, _holder=result_holder, _fd=fd):
                    try:
                        f = _fd.select_folder_finish(result)
                        _holder['file'] = f
                    except Exception:
                        _holder['file'] = None
                    try:
                        _fd.close()
                    except Exception:
                        pass
                    try:
                        _lh.quit()
                    except Exception:
                        pass

                # Fallback transient parent for portals/desktops that require it
                if parent_window is None:
                    self._logger.warning("askForExistingDirectory: no parent window found")
                    try:
                        parent_window = Gtk.Window()
                        try:
                            parent_window.set_title(self._application_title)
                        except Exception:
                            pass
                    except Exception:
                        self._logger.exception("askForExistingDirectory: failed to create fallback parent window")
                        parent_window = None

                fd.select_folder(parent_window, None, _on_opened)
                loop.run()
                gf = result_holder.get('file')
                if gf is not None:
                    try:
                        return gf.get_path() or gf.get_uri() or ""
                    except Exception:
                        return ""
                return ""
            except Exception:
                try:
                    self._logger.exception('FileDialog.select_folder failed')
                except Exception:
                    pass
                return ""
        except Exception:
            try:
                self._logger.exception("askForExistingDirectory failed")
            except Exception:
                pass
            return ""

    def askForExistingFile(self, startWith: str, filter: str, headline: str):
        """
        Prompt user to select an existing file.

        Parameters:
        - startWith: initial directory or file
        - filter: semicolon-separated string containing a list of filters (e.g. "*.txt;*.md")
        - headline: explanatory text for the dialog

        Returns: selected filename as string, or empty string if cancelled.
        """
        try:
            # try to use an active dialog window as transient parent
            parent_window = None
            try:
                for od in getattr(YDialogGtk, "_open_dialogs", []) or []:
                    try:
                        w = getattr(od, "_window", None)
                        if w:
                            parent_window = w
                            break
                    except Exception:
                        pass
            except Exception:
                parent_window = None

            if parent_window is None:
                self._logger.info("askForExistingFile: no parent window found")

            try:
                GLib.set_prgname(self._product_name or "manatools")
            except Exception:
                pass
            # Log portal-related environment to help diagnose behavior differences
            try:
                self._logger.debug("GTK_USE_PORTAL=%s", os.environ.get("GTK_USE_PORTAL"))
                self._logger.debug("XDG_CURRENT_DESKTOP=%s", os.environ.get("XDG_CURRENT_DESKTOP"))
            except Exception:
                pass

            # Use Gtk.FileDialog (GTK 4.10+) exclusively for file open
            if not hasattr(Gtk, 'FileDialog'):
                try:
                    self._logger.error('Gtk.FileDialog is not available in this GTK runtime')
                except Exception:
                    pass
                return ""

            try:
                fd = Gtk.FileDialog.new()
                try:
                    fd.set_title(headline or "Open File")
                except Exception:
                    pass
                try:
                    fd.set_modal(True)
                except Exception:
                    pass
                try:
                    fd.set_accept_label("Open")
                except Exception:
                    pass

                # filters
                try:
                    filters = self._create_gtk4_filters(filter)
                    if filters:
                        filter_list = Gio.ListStore.new(Gtk.FileFilter)
                        for file_filter in filters:
                            filter_list.append(file_filter)
                        fd.set_filters(filter_list)
                except Exception:
                    self._logger.exception("askForExistingFile: setting filters failed")
                    pass

                # Determine initial directory: requested path if valid, else default Documents
                initial_dir = None
                if startWith and os.path.exists(startWith):
                    # Set both folder and URI to improve portal compatibility
                    try:
                        target = os.path.dirname(startWith) if os.path.isfile(startWith) else startWith
                        fd.set_initial_folder(Gio.File.new_for_path(target))
                    except Exception:
                        self._logger.exception("askForExistingFile: setting initial folder failed")
                        try:
                            fd.set_initial_folder_uri(GLib.filename_to_uri(target, None))
                        except Exception:
                            pass

                loop = GLib.MainLoop()
                result_holder = {'file': None}

                def _on_opened(dialog, result, _lh=loop, _holder=result_holder, _fd=fd):
                    try:
                        f = _fd.open_finish(result)
                        _holder['file'] = f
                    except Exception:
                        _holder['file'] = None
                    try:
                        _fd.close()
                    except Exception:
                        pass
                    try:
                        _lh.quit()
                    except Exception:
                        pass

                fd.open(parent_window, None, _on_opened)
                loop.run()
                gf = result_holder.get('file')
                if gf is not None:
                    pathname = gf.get_path() or gf.get_uri() or ""
                    self._logger.debug("askForExistingFile: selected file: %s", pathname)
                    return pathname
                return ""
            except Exception:
                try:
                    self._logger.exception('FileDialog.open failed')
                except Exception:
                    pass
                return ""
        except Exception:
            return ""

    def askForSaveFileName(self, startWith: str, filter: str, headline: str):
        """
        Prompt user to choose a filename to save data.

        Returns selected filename or empty string if cancelled.
        """
        try:
            parent_window = None
            try:
                for od in getattr(YDialogGtk, "_open_dialogs", []) or []:
                    try:
                        w = getattr(od, "_window", None)
                        if w:
                            parent_window = w
                            break
                    except Exception:
                        pass
            except Exception:
                parent_window = None

            try:
                GLib.set_prgname(self._product_name or "manatools")
            except Exception:
                pass

            # Use Gtk.FileDialog (GTK 4.10+) exclusively for save
            if not hasattr(Gtk, 'FileDialog'):
                try:
                    self._logger.error('Gtk.FileDialog is not available in this GTK runtime')
                except Exception:
                    pass
                return ""

            try:
                fd = Gtk.FileDialog.new()
                try:
                    fd.set_title(headline or "Save File")
                except Exception:
                    pass
                try:
                    fd.set_modal(True)
                except Exception:
                    pass

                if filter:
                    try:
                        filters = self._create_gtk4_filters(filter)
                        if filters:
                            filter_list = Gio.ListStore.new(Gtk.FileFilter)
                            for file_filter in filters:
                                filter_list.append(file_filter)
                            fd.set_filters(filter_list)
                    except Exception:
                        self._logger.exception("askForSaveFileName: setting filters failed")

                if startWith and os.path.exists(startWith):
                    try:
                        target = os.path.dirname(startWith) if os.path.isfile(startWith) else startWith
                        fd.set_initial_folder(Gio.File.new_for_path(target))
                    except Exception:
                        self._logger.exception("askForSaveFileName: setting initial folder failed")
                        try:
                            fd.set_initial_folder_uri(GLib.filename_to_uri(target, None))
                        except Exception:
                            pass

                loop = GLib.MainLoop()
                result_holder = {'file': None}

                def _on_saved(dialog, result, _lh=loop, _holder=result_holder, _fd=fd):
                    try:
                        f = _fd.save_finish(result)
                        _holder['file'] = f
                    except Exception:
                        _holder['file'] = None
                    try:
                        _fd.close()
                    except Exception:
                        pass
                    try:
                        _lh.quit()
                    except Exception:
                        pass

                # Fallback transient parent creation if none present
                if parent_window is None:
                    self._logger.warning("askForSaveFileName: no parent window found")
                    try:
                        parent_window = Gtk.Window()
                        try:
                            parent_window.set_title(self._application_title)
                        except Exception:
                            pass
                    except Exception:
                        self._logger.exception("askForSaveFileName: failed to create fallback parent window")
                        parent_window = None

                fd.save(parent_window, None, _on_saved)
                loop.run()
                gf = result_holder.get('file')
                if gf is not None:
                    try:
                        return gf.get_path() or gf.get_uri() or ""
                    except Exception:
                        return ""
                return ""
            except Exception:
                try:
                    self._logger.exception('FileDialog.save failed')
                except Exception:
                    pass
                return ""
        except Exception:
            try:
                self._logger.exception("askForSaveFileName failed")
            except Exception:
                pass
            return ""

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
    def createMultiLineEdit(self, parent, label):
        return YMultiLineEditGtk(parent, label)
    def createIntField(self, parent, label, minVal, maxVal, initialVal):
        return YIntFieldGtk(parent, label, minVal, maxVal, initialVal)
    
    def createCheckBox(self, parent, label, is_checked=False):
        return YCheckBoxGtk(parent, label, is_checked)
    
    def createPasswordField(self, parent, label):
        return YInputFieldGtk(parent, label, password_mode=True)
    
    def createComboBox(self, parent, label, editable=False):
        return YComboBoxGtk(parent, label, editable)
    
    def createSelectionBox(self, parent, label):
        return YSelectionBoxGtk(parent, label)

    #Multi-selection box variant
    def createMultiSelectionBox(self, parent, label):
        return YSelectionBoxGtk(parent, label, multi_selection=True)

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

    def createMinWidth(self, parent, minWidth: int):
        a = YAlignmentGtk(parent)
        try:
            a._min_width_px = int(minWidth)
        except Exception:
            pass
        return a

    def createMinHeight(self, parent, minHeight: int):
        a = YAlignmentGtk(parent)
        try:
            a._min_height_px = int(minHeight)
        except Exception:
            pass
        return a

    def createMinSize(self, parent, minWidth: int, minHeight: int):
        a = YAlignmentGtk(parent)
        try:
            a._min_width_px = int(minWidth)
        except Exception:
            pass
        try:
            a._min_height_px = int(minHeight)
        except Exception:
            pass
        return a

    def createTree(self, parent, label, multiselection=False, recursiveselection = False):
        """Create a Tree widget."""
        return YTreeGtk(parent, label, multiselection, recursiveselection)

    def createTable(self, parent, header: YTableHeader, multiSelection: bool = False):
        """Create a Table widget."""
        from .backends.gtk.tablegtk import YTableGtk
        return YTableGtk(parent, header, multiSelection)

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

    def createReplacePoint(self, parent):
        """Create a ReplacePoint widget (GTK backend)."""
        return YReplacePointGtk(parent)

    def createDumbTab(self, parent):
        from .backends.gtk import YDumbTabGtk
        return YDumbTabGtk(parent)

    def createSpacing(self, parent, dim: YUIDimension, stretchable: bool = False, size_px: int = 0):
        """Create a Spacing/Stretch widget.

        - `dim`: primary dimension for spacing (YUIDimension)
        - `stretchable`: expand in primary dimension when True (minimum size = `size`)
        - `size_px`: spacing size in pixels (device units, integer)
        """
        return YSpacingGtk(parent, dim, stretchable, size_px)

    def createImage(self, parent, imageFileName):
        """Create an image widget."""
        return YImageGtk(parent, imageFileName)
    
    # Create a Spacing widget variant
    def createHStretch(self, parent):
        """Create a Horizontal Stretch widget."""
        return self.createSpacing(parent, YUIDimension.Horizontal, stretchable=True)
    
    def createVStretch(self, parent):
        """Create a Vertical Stretch widget."""
        return self.createSpacing(parent, YUIDimension.Vertical, stretchable=True)
    
    def createHSpacing(self, parent, size_px: int = 8):
        """Create a Horizontal Spacing widget."""
        return self.createSpacing(parent, YUIDimension.Horizontal, stretchable=False, size_px=size_px)

    def createSlider(self, parent, label: str, minVal: int, maxVal: int, initialVal: int):
        """Create a Slider widget (GTK backend)."""
        from .backends.gtk import YSliderGtk
        return YSliderGtk(parent, label, minVal, maxVal, initialVal)
    
    def createVSpacing(self, parent, size_px: int = 16):
        """Create a Vertical Spacing widget."""
        return self.createSpacing(parent, YUIDimension.Vertical, stretchable=False, size_px=size_px)

    def createDateField(self, parent, label):
        """Create a DateField widget (GTK backend)."""
        return YDateFieldGtk(parent, label)

    def createFrame(self, parent, label: str=""):
        """Create a Frame widget."""
        return YFrameGtk(parent, label)
