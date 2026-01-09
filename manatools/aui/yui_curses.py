"""
NCurses backend implementation for YUI
"""

import curses
import curses.ascii
import sys
import os
import time
import fnmatch
from .yui_common import *
from .backends.curses import *

class YUICurses:
    def __init__(self):
        self._widget_factory = YWidgetFactoryCurses()
        self._optional_widget_factory = None
        self._application = YApplicationCurses()
        self._stdscr = None
        self._colors_initialized = False
        self._running = False
        
        # Initialize curses
        self._init_curses()
    
    def _init_curses(self):
        try:
            self._stdscr = curses.initscr()
            curses.noecho()
            curses.cbreak()
            curses.curs_set(1)  # Show cursor
            self._stdscr.keypad(True)
            
            # Enable colors if available
            if curses.has_colors():
                curses.start_color()
                curses.use_default_colors()
                self._colors_initialized = True
                # Define some color pairs
                curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
                curses.init_pair(2, curses.COLOR_YELLOW, -1)
                curses.init_pair(3, curses.COLOR_GREEN, -1)
                curses.init_pair(4, curses.COLOR_RED, -1)
        except Exception as e:
            print(f"Error initializing curses: {e}")
            self._cleanup_curses()
            raise
    
    def _cleanup_curses(self):
        try:
            if self._stdscr:
                curses.nocbreak()
                self._stdscr.keypad(False)
                curses.echo()
                curses.curs_set(1)
                curses.endwin()
        except:
            pass
    
    def __del__(self):
        self._cleanup_curses()
    
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

class YApplicationCurses:
    def __init__(self):
        self._application_title = "manatools Curses Application"
        self._product_name = "manatools AUI Curses"
        self._icon_base_path = ""
        self._icon = ""
        # About dialog metadata
        self._app_name = ""
        self._version = ""
        self._authors = ""
        self._description = ""
        self._license = ""
        self._credits = ""
        self._information = ""
        self._logo = ""
        # Default directories
        try:
            self._default_documents_dir = os.path.expanduser('~/Documenti')
        except Exception:
            self._default_documents_dir = os.path.expanduser('~')

    def iconBasePath(self):
        return self._icon_base_path
    
    def setIconBasePath(self, new_icon_base_path):
        self._icon_base_path = new_icon_base_path
    
    def setProductName(self, product_name):
        self._product_name = product_name
    
    def productName(self):
        return self._product_name

    def setApplicationIcon(self, Icon):
        """Set the application icon."""
        self._icon = Icon

    # --- About metadata getters/setters ---
    def setApplicationName(self, name: str):
        self._app_name = name or ""

    def applicationName(self) -> str:
        return self._app_name or self._product_name or ""

    def setVersion(self, version: str):
        self._version = version or ""

    def version(self) -> str:
        return self._version or ""

    def setAuthors(self, authors: str):
        self._authors = authors or ""

    def authors(self) -> str:
        return self._authors or ""

    def setDescription(self, description: str):
        self._description = description or ""

    def description(self) -> str:
        return self._description or ""

    def setLicense(self, license_text: str):
        self._license = license_text or ""

    def license(self) -> str:
        return self._license or ""

    def setCredits(self, credits: str):
        self._credits = credits or ""

    def credits(self) -> str:
        return self._credits or ""

    def setInformation(self, information: str):
        self._information = information or ""

    def information(self) -> str:
        return self._information or ""

    def setLogo(self, logo_path: str):
        self._logo = logo_path or ""

    def logo(self) -> str:
        return self._logo or ""

    def askForExistingDirectory(self, startDir: str, headline: str):
        """
        NCurses overlay dialog to select an existing directory.
        Presents a navigable list of directories similar to a simple file manager.
        """
        try:
            start_dir = startDir if (startDir and os.path.isdir(startDir)) else os.path.expanduser('~')
            return self._browse_paths(start_dir, select_file=False, headline=headline or "Select Directory", reason='directory')
        except Exception:
            return ""

    def askForExistingFile(self, startWith: str, filter: str, headline: str):
        """
        NCurses overlay dialog to select an existing file.
        Shows a navigable list of directories and files, honoring simple filters like "*.txt;*.md".
        """
        try:
            if startWith and os.path.isfile(startWith):
                start_dir = os.path.dirname(startWith)
            elif startWith and os.path.isdir(startWith):
                start_dir = startWith
            else:
                # Default to Documents if available, else home
                start_dir = self._default_documents_dir if os.path.isdir(self._default_documents_dir) else os.path.expanduser('~')
            return self._browse_paths(start_dir, select_file=True, headline=headline or "Open File", filter_str=filter, reason='file')
        except Exception:
            return ""

    def askForSaveFileName(self, startWith: str, filter: str, headline: str):
        """
        NCurses overlay to choose a filename: navigate directories and type the name.
        """
        try:
            if startWith and os.path.isfile(startWith):
                start_dir = os.path.dirname(startWith)
                default_name = os.path.basename(startWith)
            elif startWith and os.path.isdir(startWith):
                start_dir = startWith
                default_name = ""
            else:
                start_dir = self._default_documents_dir if os.path.isdir(self._default_documents_dir) else os.path.expanduser('~')
                default_name = ""
            return self._browse_paths(start_dir, select_file=True, headline=headline or "Save File", filter_str=filter, reason='save', default_name=default_name)
        except Exception:
            return ""

    def applicationIcon(self):
        """Get the application icon."""
        return self._icon

    def setApplicationTitle(self, title):
        """Set the application title."""
        self._application_title = title
        # Update terminal/window title for xterm-like terminals when stdout is a TTY
        escape_sequences = [
            f"\033]0;{title}\007",   # Standard
            f"\033]1;{title}\007",   # Icon name
            f"\033]2;{title}\007",   # Window title
            f"\033]30;{title}\007",  # Konsole variant 1
            f"\033]31;{title}\007",  # Konsole variant 2
        ]
        try:
            for seq in escape_sequences:
                sys.stdout.write(seq)
            sys.stdout.flush()            
        except Exception:
            pass

    def applicationTitle(self):
        """Get the application title."""
        return self._application_title

    def setApplicationIcon(self, Icon):
        """Set the application title."""
        self._icon = Icon

    def applicationIcon(self):
        """Get the application title."""
        return self.__icon

    # --- Internal helpers for ncurses file/directory chooser ---
    def _parse_filter_patterns(self, filter_str: str):
        try:
            if not filter_str:
                return []
            parts = [p.strip() for p in filter_str.split(';') if p.strip()]
            return parts
        except Exception:
            return []

    def _list_entries(self, current_dir: str, select_file: bool, patterns):
        """Return list of (label, path, type) for entries under current_dir.
        type is 'dir' or 'file'. If select_file is True, apply patterns to files.
        """
        entries = []
        try:
            # Add parent directory entry
            parent = os.path.dirname(current_dir.rstrip(os.sep)) or current_dir
            if parent and parent != current_dir:
                entries.append(("..", parent, 'dir'))
            # List directory contents
            with os.scandir(current_dir) as it:
                dirs = []
                files = []
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            dirs.append((e.name + '/', e.path, 'dir'))
                        elif e.is_file(follow_symlinks=False):
                            if not select_file:
                                continue
                            if not patterns:
                                files.append((e.name, e.path, 'file'))
                            else:
                                for pat in patterns:
                                    if fnmatch.fnmatch(e.name, pat):
                                        files.append((e.name, e.path, 'file'))
                                        break
                    except Exception:
                        pass
            # Sort directories and files separately
            dirs.sort(key=lambda x: x[0].lower())
            files.sort(key=lambda x: x[0].lower())
            entries.extend(dirs)
            entries.extend(files)
        except Exception:
            # On failure, just return parent
            pass
        return entries

    def _browse_paths(self, start_dir: str, select_file: bool, headline: str, filter_str: str = "", reason: str = "file", default_name: str = ""):
        """
            Unified ncurses overlay to navigate directories and pick a file, directory or save path.
            - `reason` in ('file', 'directory', 'save') controls final behavior.
            - Uses a `YTableCurses` with a single "Name" column to list entries.
            - Avoids race between refresh and button-based selection by keeping
              the current selection in a label/input field that is updated on
              SelectionChanged and read when the Select/Save button is pressed.
        """
        current_dir = start_dir if os.path.isdir(start_dir) else os.path.expanduser('~')
        patterns = self._parse_filter_patterns(filter_str)

        # Build dialog UI
        dlg = YDialogCurses(YDialogType.YPopupDialog, YDialogColorMode.YDialogNormalColor)
        root = YVBoxCurses(dlg)
        YLabelCurses(root, headline, isHeading=True)
        path_lbl = YLabelCurses(root, f"Current: {current_dir}")

        # Table with single "Name" column
        header = YTableHeader()
        header.addColumn("Name")
        table = YTableCurses(root, header, multiSelection=False)
        try:
            table.setWeight(YUIDimension.YD_VERT, 1)
        except Exception:
            pass

        # Selection preview and optional filename input (useful for save)
        selected_lbl = YLabelCurses(root, "Selected: ")
        filename_input = None
        if reason == 'save':
            filename_input = YInputFieldCurses(root, label="Filename:")
            try:
                if default_name:
                    filename_input.setValue(default_name)
            except Exception:
                pass

        # Buttons
        buttons = YHBoxCurses(root)
        btn_label = "Save" if reason == 'save' else "Select"
        btn_select = YPushButtonCurses(buttons, btn_label)
        btn_cancel = YPushButtonCurses(buttons, "Cancel")

        selected_item_data = None

        def refresh_listing(dir_path):
            nonlocal selected_item_data
            try:
                table.deleteAllItems()
                for (label, path, typ) in self._list_entries(dir_path, select_file, patterns):
                    it = YTableItem(label)
                    try:
                        it.addCell(label)
                        it.setData({'path': path, 'type': typ})
                    except Exception:
                        pass
                    table.addItem(it)
                # reset selection state when navigating
                selected_item_data = None
                try:
                    selected_lbl.setText("Selected: ")
                except Exception:
                    pass
            except Exception:
                pass

        refresh_listing(current_dir)
        try:
            dlg.open()
        except Exception:
            return ""

        # Event loop
        result = ""
        while True:
            ev = dlg.waitForEvent()
            if isinstance(ev, YCancelEvent):
                result = ""
                break
            if isinstance(ev, YWidgetEvent):
                w = ev.widget()
                if w == btn_cancel and ev.reason() == YEventReason.Activated:
                    result = ""
                    break

                # Select/Save pressed: read from selection preview / input field
                if w == btn_select and ev.reason() == YEventReason.Activated:
                    try:
                        # If save: prefer filename_input value; if a file was selected,
                        # use that name as default when input is empty.
                        if reason == 'save':
                            name = None
                            try:
                                if filename_input is not None:
                                    name = filename_input.value()
                            except Exception:
                                name = None
                            if selected_item_data and selected_item_data.get('type') == 'file':
                                sel_base = os.path.basename(selected_item_data.get('path'))
                                if not name:
                                    name = sel_base
                            if name:
                                result = os.path.join(current_dir, name)
                                break
                            # if no name, ignore press
                            continue

                        # Directory selection: if a directory row is selected, return it,
                        # otherwise return current_dir
                        if reason == 'directory':
                            if selected_item_data and selected_item_data.get('type') == 'dir':
                                result = selected_item_data.get('path')
                            else:
                                result = current_dir
                            break

                        # File selection: if a file row is selected, return it
                        if reason == 'file':
                            if selected_item_data and selected_item_data.get('type') == 'file':
                                result = selected_item_data.get('path')
                                break
                            # nothing selected: ignore
                            continue
                    except Exception:
                        continue

                # Table selection changed: either navigate into directories or update preview
                if w == table and ev.reason() == YEventReason.SelectionChanged:
                    try:
                        sel = table.selectedItems()
                        if not sel:
                            selected_item_data = None
                            try:
                                selected_lbl.setText("Selected: ")
                            except Exception:
                                pass
                            continue
                        item = sel[0]
                        data = item.data() if hasattr(item, 'data') else None
                        if not data or 'path' not in data:
                            selected_item_data = None
                            try:
                                selected_lbl.setText("Selected: ")
                            except Exception:
                                pass
                            continue
                        if data.get('type') == 'dir':
                            # navigate into directory
                            current_dir = data['path']
                            try:
                                path_lbl.setText(f"Current: {current_dir}")
                            except Exception:
                                pass
                            refresh_listing(current_dir)
                            continue
                        else:
                            # file selected: update preview and prefill filename when saving
                            selected_item_data = data
                            try:
                                selected_lbl.setText(f"Selected: {os.path.basename(data.get('path'))}")
                            except Exception:
                                pass
                            if reason == 'save' and filename_input is not None:
                                try:
                                    filename_input.setValue(os.path.basename(data.get('path')))
                                except Exception:
                                    pass
                    except Exception:
                        continue

        try:
            dlg.destroy()
        except Exception:
            pass
        return result


class YWidgetFactoryCurses:
    def __init__(self):
        pass
    
    def createMainDialog(self, color_mode=YDialogColorMode.YDialogNormalColor):
        return YDialogCurses(YDialogType.YMainDialog, color_mode)

    def createPopupDialog(self, color_mode=YDialogColorMode.YDialogNormalColor):
        return YDialogCurses(YDialogType.YMainDialog, color_mode)
    
    def createVBox(self, parent):
        return YVBoxCurses(parent)
    
    def createHBox(self, parent):
        return YHBoxCurses(parent)
    
    def createLabel(self, parent, text, isHeading=False, isOutputField=False):
        return YLabelCurses(parent, text, isHeading, isOutputField)
    
    def createHeading(self, parent, label):
        return YLabelCurses(parent, label, isHeading=True)
    
    def createInputField(self, parent, label, password_mode=False):
        return YInputFieldCurses(parent, label, password_mode)
    def createIntField(self, parent, label, minVal, maxVal, initialVal):
        return YIntFieldCurses(parent, label, minVal, maxVal, initialVal)
    def createMultiLineEdit(self, parent, label):
        return YMultiLineEditCurses(parent, label)
    
    def createPushButton(self, parent, label):
        return YPushButtonCurses(parent, label)
    
    def createCheckBox(self, parent, label, is_checked=False):
        return YCheckBoxCurses(parent, label, is_checked)
    
    def createComboBox(self, parent, label, editable=False):
        return YComboBoxCurses(parent, label, editable)
    
    def createSelectionBox(self, parent, label):
        return YSelectionBoxCurses(parent, label)

    #Multi-selection box variant
    def createMultiSelectionBox(self, parent, label):
        return YSelectionBoxCurses(parent, label, multi_selection=True)

    # Alignment helpers
    def createLeft(self, parent):
        return YAlignmentCurses(parent, horAlign=YAlignmentType.YAlignBegin,  vertAlign=YAlignmentType.YAlignUnchanged)

    def createRight(self, parent):
        return YAlignmentCurses(parent, horAlign=YAlignmentType.YAlignEnd, vertAlign=YAlignmentType.YAlignUnchanged)

    def createTop(self, parent):
        return YAlignmentCurses(parent, horAlign=YAlignmentType.YAlignUnchanged,   vertAlign=YAlignmentType.YAlignBegin)

    def createBottom(self, parent):
        return YAlignmentCurses(parent, horAlign=YAlignmentType.YAlignUnchanged,   vertAlign=YAlignmentType.YAlignEnd)

    def createHCenter(self, parent):
        return YAlignmentCurses(parent, horAlign=YAlignmentType.YAlignCenter, vertAlign=YAlignmentType.YAlignUnchanged)

    def createVCenter(self, parent):
        return YAlignmentCurses(parent, horAlign=YAlignmentType.YAlignUnchanged,      vertAlign=YAlignmentType.YAlignCenter)

    def createHVCenter(self, parent):
        return YAlignmentCurses(parent, horAlign=YAlignmentType.YAlignCenter, vertAlign=YAlignmentType.YAlignCenter)

    def createAlignment(self, parent, horAlignment: YAlignmentType, vertAlignment: YAlignmentType):
        """Create a generic YAlignment using YAlignmentType enums (or compatible specs)."""
        return YAlignmentCurses(parent, horAlign=horAlignment, vertAlign=vertAlignment)

    def createMinWidth(self, parent, minWidth: int):
        a = YAlignmentCurses(parent, horAlign=YAlignmentType.YAlignUnchanged, vertAlign=YAlignmentType.YAlignUnchanged)
        try:
            a.setMinWidth(int(minWidth))
        except Exception:
            pass
        return a

    def createMinHeight(self, parent, minHeight: int):
        a = YAlignmentCurses(parent, horAlign=YAlignmentType.YAlignUnchanged, vertAlign=YAlignmentType.YAlignUnchanged)
        try:
            a.setMinHeight(int(minHeight))
        except Exception:
            pass
        return a

    def createMinSize(self, parent, minWidth: int, minHeight: int):
        a = YAlignmentCurses(parent, horAlign=YAlignmentType.YAlignUnchanged, vertAlign=YAlignmentType.YAlignUnchanged)
        try:
            a.setMinSize(int(minWidth), int(minHeight))
        except Exception:
            pass
        return a

    def createTree(self, parent, label, multiselection=False, recursiveselection = False):
        """Create a Tree widget."""
        return YTreeCurses(parent, label, multiselection, recursiveselection)    
 
    def createFrame(self, parent, label: str=""):
        """Create a Frame widget."""
        return YFrameCurses(parent, label)

    def createCheckBoxFrame(self, parent, label: str = "", checked: bool = False):
        """Create a CheckBox Frame widget."""
        return YCheckBoxFrameCurses(parent, label, checked)
    
    def createProgressBar(self, parent, label, max_value=100):
        """Create a Progress Bar widget."""
        return YProgressBarCurses(parent, label, max_value)

    def createRadioButton(self, parent, label="", isChecked=False):
        """Create a Radio Button widget."""
        return YRadioButtonCurses(parent, label, isChecked)

    def createTable(self, parent, header: YTableHeader, multiSelection=False):
        """Create a Table widget (curses backend)."""
        return YTableCurses(parent, header, multiSelection)

    def createRichText(self, parent, text: str = "", plainTextMode: bool = False):
        """Create a RichText widget (curses backend)."""
        return YRichTextCurses(parent, text, plainTextMode)

    def createMenuBar(self, parent):
        """Create a MenuBar widget (curses backend)."""
        return YMenuBarCurses(parent)

    def createReplacePoint(self, parent):
        """Create a ReplacePoint widget (curses backend)."""
        return YReplacePointCurses(parent)

    def createDumbTab(self, parent):
        """Create a DumbTab widget (curses backend)."""
        return YDumbTabCurses(parent)

    def createSpacing(self, parent, dim: YUIDimension, stretchable: bool = False, size_px: int = 0):
        """Create a Spacing/Stretch widget.

        - `dim`: primary dimension for spacing (YUIDimension)
        - `stretchable`: expand in primary dimension when True (minimum size = `size`)
        - `size_px`: spacing size in pixels (integer), converted to character cells
            using 8 px/char horizontally and ~16 px/row vertically.
        """
        return YSpacingCurses(parent, dim, stretchable, size_px)

    def createImage(self, parent, imageFileName):
        """Create an image widget as an empty frame for curses."""
        return YImageCurses(parent, imageFileName)
    
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
    
    def createVSpacing(self, parent, size_px: int = 16):
        """Create a Vertical Spacing widget."""
        return self.createSpacing(parent, YUIDimension.Vertical, stretchable=False, size_px=size_px)

    def createSlider(self, parent, label: str, minVal: int, maxVal: int, initialVal: int):
        """Create a Slider widget (ncurses backend)."""
        return YSliderCurses(parent, label, minVal, maxVal, initialVal)

    def createDateField(self, parent, label):
        """Create a DateField widget (curses backend)."""
        return YDateFieldCurses(parent, label)

    def createLogView(self, parent, label, visibleLines, storedLines=0):
        """Create a LogView widget (ncurses backend)."""
        from .backends.curses import YLogViewCurses
        try:
            return YLogViewCurses(parent, label, visibleLines, storedLines)
        except Exception as e:
            logging.getLogger(__name__).exception("Failed to create YLogViewCurses: %s", e)
            raise

    def createTimeField(self, parent, label):
        """Create a TimeField widget (ncurses backend)."""
        from .backends.curses import YTimeFieldCurses
        try:
            return YTimeFieldCurses(parent, label)
        except Exception as e:
            logging.getLogger(__name__).exception("Failed to create YTimeFieldCurses: %s", e)
            raise

