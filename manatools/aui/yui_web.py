"""
Web backend implementation for YUI

This backend renders widgets as HTML and serves them via HTTP.
User interaction is handled via WebSocket for real-time communication.
"""

import logging
import os
import shutil
import subprocess
from .yui_common import (
    YDialogType,
    YDialogColorMode,
    YUIDimension,
    YTableHeader,
    YTableItem,
    YCancelEvent,
    YWidgetEvent,
    YEventReason,
    list_entries,
    parse_filter_patterns,
)


class YUIWeb:
    """Web backend YUI implementation."""
    
    def __init__(self):
        self._widget_factory = YWidgetFactoryWeb()
        self._optional_widget_factory = None
        self._application = YApplicationWeb()
        self._logger = logging.getLogger(f"manatools.aui.web.{self.__class__.__name__}")

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

    def shutdown(self):
        """Close every open dialog and stop the HTTP/WebSocket server.

        Applications call this on exit; the ncurses backend uses it to restore
        the terminal.  Here it notifies connected browsers and releases the
        listening socket so the process can terminate cleanly.
        """
        try:
            from .backends.web.dialogweb import YDialogWeb
            with YDialogWeb._open_dialogs_lock:
                dialogs = list(YDialogWeb._open_dialogs)
            # Destroy popups first, main dialog (which owns the server) last.
            for dialog in reversed(dialogs):
                try:
                    dialog.destroy()
                except Exception:
                    self._logger.debug("shutdown: failed to destroy %s", dialog, exc_info=True)
        except Exception:
            self._logger.debug("shutdown: no dialogs to close", exc_info=True)


class YApplicationWeb:
    """Web backend application settings."""
    
    def __init__(self):
        self._application_title = "ManaTools Web Application"
        self._product_name = "ManaTools AUI Web"
        self._icon_base_path = None
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
        self._logger = logging.getLogger(f"manatools.aui.web.{self.__class__.__name__}")

    def iconBasePath(self):
        return self._icon_base_path

    def setIconBasePath(self, new_icon_base_path):
        self._icon_base_path = new_icon_base_path

    def setProductName(self, product_name):
        self._product_name = product_name

    def productName(self):
        return self._product_name

    def setApplicationTitle(self, title):
        self._application_title = title

    def applicationTitle(self):
        return self._application_title

    def setApplicationIcon(self, icon):
        self._icon = icon

    def applicationIcon(self):
        return self._icon

    # About metadata
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

    def isTextMode(self) -> bool:
        """Return True so callers start a GLib main loop for D-Bus signal dispatch.

        The web backend has no native event loop that processes GLib/D-Bus
        signals.  Returning True mirrors the ncurses backend's behaviour and
        causes dnfdragora (and similar apps) to start a GLib.MainLoop thread,
        which is required for dbus-python async signals to be delivered.
        """
        return True

    def busyCursor(self):
        """Show a full-screen busy overlay in the browser."""
        self._broadcast_busy(True)

    def normalCursor(self):
        """Hide the busy overlay in the browser."""
        self._broadcast_busy(False)

    def _broadcast_busy(self, state: bool):
        try:
            from .backends.web.dialogweb import YDialogWeb
            root = next((d for d in YDialogWeb._open_dialogs if d._server is not None), None)
            if root:
                if not state:
                    # Flush all queued widget updates before hiding the overlay
                    # so the browser receives and applies them first.
                    root._flush_all_pending_updates()
                root._broadcast({"type": "busy", "state": state})
        except Exception:
            pass

    # --- File and directory choosers ---
    #
    # The browser's own file picker cannot be used here: it yields a sandboxed
    # File object and a fake path, while callers expect a real path they open
    # themselves server-side (see test/test_file_dialogs.py).  So, like the
    # ncurses backend, the web backend renders its own browser from AUI widgets
    # and lists the server's filesystem.  Server and browser are the same
    # machine (the server binds 127.0.0.1 only), so this exposes nothing the
    # Qt/GTK/ncurses backends do not.

    def _documents_dir(self) -> str:
        """Return the user's documents directory, falling back to home."""
        try:
            xdg = shutil.which("xdg-user-dir")
            if xdg:
                out = subprocess.run(
                    [xdg, "DOCUMENTS"],
                    capture_output=True, text=True, timeout=2,
                ).stdout.strip()
                if out and os.path.isdir(out):
                    return out
        except Exception:
            self._logger.debug("xdg-user-dir lookup failed", exc_info=True)
        return os.path.expanduser("~")

    def _start_dir(self, start_with: str):
        """Resolve the directory a chooser should open at, plus a default name."""
        if start_with and os.path.isfile(start_with):
            return os.path.dirname(start_with), os.path.basename(start_with)
        if start_with and os.path.isdir(start_with):
            return start_with, ""
        return self._documents_dir(), ""

    def askForExistingDirectory(self, startDir: str, headline: str):
        """Prompt for an existing directory. Returns its path, or "" if cancelled."""
        try:
            start = startDir if startDir and os.path.isdir(startDir) else self._documents_dir()
            return self._browse_paths(
                start, select_file=False,
                headline=headline or "Select Directory", reason='directory')
        except Exception:
            self._logger.exception("askForExistingDirectory failed")
            return ""

    def askForExistingFile(self, startWith: str, filter: str, headline: str):
        """Prompt for an existing file. Returns its path, or "" if cancelled."""
        try:
            start, _name = self._start_dir(startWith)
            return self._browse_paths(
                start, select_file=True, headline=headline or "Open File",
                filter_str=filter, reason='file')
        except Exception:
            self._logger.exception("askForExistingFile failed")
            return ""

    def askForSaveFileName(self, startWith: str, filter: str, headline: str):
        """Prompt for a filename to save to. Returns its path, or "" if cancelled."""
        try:
            start, default_name = self._start_dir(startWith)
            return self._browse_paths(
                start, select_file=True, headline=headline or "Save File",
                filter_str=filter, reason='save', default_name=default_name)
        except Exception:
            self._logger.exception("askForSaveFileName failed")
            return ""

    def _browse_paths(self, start_dir: str, select_file: bool, headline: str,
                      filter_str: str = "", reason: str = "file",
                      default_name: str = ""):
        """Modal filesystem browser shared by the three chooser entry points.

        Mirrors the ncurses browser: a single-column table of entries where
        selecting a directory row navigates into it (the web table has no
        double-click, only single-click SelectionChanged) and selecting a file
        row updates the preview.  *reason* decides what the Select/Save button
        returns; see the branches below.
        """
        from .yui import YUI

        factory = YUI.widgetFactory()
        current_dir = start_dir if os.path.isdir(start_dir) else os.path.expanduser('~')
        patterns = parse_filter_patterns(filter_str)

        dlg = factory.createPopupDialog()
        result = ""
        try:
            root = factory.createVBox(dlg)
            factory.createHeading(root, headline)
            # Path labels are output fields: filenames are data, so a literal
            # '&' must not be read as shortcut notation and underline a letter.
            path_lbl = factory.createLabel(
                root, f"Current: {current_dir}", isOutputField=True)

            header = YTableHeader()
            header.addColumn("Name")
            sized = factory.createMinSize(root, 60, 16)
            table = factory.createTable(sized, header)

            selected_lbl = factory.createLabel(root, "Selected: ", isOutputField=True)
            filename_input = None
            if reason == 'save':
                filename_input = factory.createInputField(root, "Filename:")
                if default_name:
                    filename_input.setValue(default_name)

            buttons = factory.createHBox(root)
            factory.createHStretch(buttons)
            btn_select = factory.createPushButton(
                buttons, "&Save" if reason == 'save' else "&Select")
            btn_cancel = factory.createPushButton(buttons, "&Cancel")

            selected_item_data = None

            def refresh_listing(dir_path):
                nonlocal selected_item_data
                table.deleteAllItems()
                for (label, path, typ) in list_entries(dir_path, select_file, patterns):
                    item = YTableItem(label)
                    item.addCell(label)
                    item.setData({'path': path, 'type': typ})
                    table.addItem(item)
                selected_item_data = None
                selected_lbl.setText("Selected: ")

            refresh_listing(current_dir)
            dlg.open()

            while True:
                ev = dlg.waitForEvent()
                if isinstance(ev, YCancelEvent):
                    result = ""
                    break

                if not isinstance(ev, YWidgetEvent):
                    continue

                widget = ev.widget()

                if widget == btn_cancel and ev.reason() == YEventReason.Activated:
                    result = ""
                    break

                if widget == btn_select and ev.reason() == YEventReason.Activated:
                    if reason == 'save':
                        name = filename_input.value() if filename_input else ""
                        if not name and selected_item_data \
                                and selected_item_data.get('type') == 'file':
                            name = os.path.basename(selected_item_data['path'])
                        if not name:
                            continue  # nothing to save as: ignore the press
                        result = os.path.join(current_dir, name)
                        break

                    if reason == 'directory':
                        result = current_dir
                        break

                    # reason == 'file': require an actual file selection
                    if selected_item_data and selected_item_data.get('type') == 'file':
                        result = selected_item_data['path']
                        break
                    continue

                if widget == table and ev.reason() == YEventReason.SelectionChanged:
                    selected = table.selectedItems()
                    if not selected:
                        selected_item_data = None
                        selected_lbl.setText("Selected: ")
                        continue

                    data = selected[0].data()
                    if not data or 'path' not in data:
                        selected_item_data = None
                        selected_lbl.setText("Selected: ")
                        continue

                    if data.get('type') == 'dir':
                        current_dir = data['path']
                        path_lbl.setText(f"Current: {current_dir}")
                        refresh_listing(current_dir)
                        continue

                    selected_item_data = data
                    selected_lbl.setText(f"Selected: {data['path']}")
                    if reason == 'save' and filename_input is not None:
                        filename_input.setValue(os.path.basename(data['path']))
        finally:
            try:
                dlg.destroy()
            except Exception:
                self._logger.debug("file chooser: destroy failed", exc_info=True)

        return result


class YWidgetFactoryWeb:
    """Factory for creating web-based widgets."""
    
    def __init__(self):
        self._logger = logging.getLogger(f"manatools.aui.web.{self.__class__.__name__}")

    # --- Dialogs ---
    
    def createMainDialog(self, color_mode=YDialogColorMode.YDialogNormalColor):
        from .backends.web import YDialogWeb
        return YDialogWeb(YDialogType.YMainDialog, color_mode)

    def createPopupDialog(self, color_mode=YDialogColorMode.YDialogNormalColor):
        from .backends.web import YDialogWeb
        return YDialogWeb(YDialogType.YPopupDialog, color_mode)

    # --- Layout ---
    
    def createVBox(self, parent):
        from .backends.web import YVBoxWeb
        return YVBoxWeb(parent)

    def createHBox(self, parent):
        from .backends.web import YHBoxWeb
        return YHBoxWeb(parent)

    def createFrame(self, parent, label: str = ""):
        from .backends.web import YFrameWeb
        return YFrameWeb(parent, label)

    # --- Basic Widgets ---
    
    def createLabel(self, parent, text, isHeading=False, isOutputField=False):
        from .backends.web import YLabelWeb
        return YLabelWeb(parent, text, isHeading, isOutputField)

    def createHeading(self, parent, label):
        from .backends.web import YLabelWeb
        return YLabelWeb(parent, label, isHeading=True)

    def createPushButton(self, parent, label):
        from .backends.web import YPushButtonWeb
        return YPushButtonWeb(parent, label)

    def createIconButton(self, parent, iconName, fallbackTextLabel):
        from .backends.web import YPushButtonWeb
        # icon_only=False: always render the text label alongside the icon.
        # The label acts as a visible fallback when the icon file cannot be
        # found on the server, which is the common case on web-only deployments.
        return YPushButtonWeb(parent, label=fallbackTextLabel, icon_name=iconName, icon_only=False)

    def createInputField(self, parent, label, password_mode=False):
        from .backends.web import YInputFieldWeb
        return YInputFieldWeb(parent, label, password_mode)

    def createPasswordField(self, parent, label):
        from .backends.web import YInputFieldWeb
        return YInputFieldWeb(parent, label, password_mode=True)

    def createCheckBox(self, parent, label, is_checked=False):
        from .backends.web import YCheckBoxWeb
        return YCheckBoxWeb(parent, label, is_checked)

    def createComboBox(self, parent, label, editable=False):
        from .backends.web import YComboBoxWeb
        return YComboBoxWeb(parent, label, editable)

    def createSelectionBox(self, parent, label):
        from .backends.web import YSelectionBoxWeb
        return YSelectionBoxWeb(parent, label)

    def createMultiSelectionBox(self, parent, label):
        from .backends.web import YSelectionBoxWeb
        return YSelectionBoxWeb(parent, label, multi_selection=True)

    def createProgressBar(self, parent, label, max_value=100):
        from .backends.web import YProgressBarWeb
        return YProgressBarWeb(parent, label, max_value)

    # --- Alignment ---
    
    def createLeft(self, parent):
        from .backends.web import YAlignmentWeb
        from .yui_common import YAlignmentType
        return YAlignmentWeb(parent, horAlign=YAlignmentType.YAlignBegin, vertAlign=YAlignmentType.YAlignUnchanged)

    def createRight(self, parent):
        from .backends.web import YAlignmentWeb
        from .yui_common import YAlignmentType
        return YAlignmentWeb(parent, horAlign=YAlignmentType.YAlignEnd, vertAlign=YAlignmentType.YAlignUnchanged)

    def createTop(self, parent):
        from .backends.web import YAlignmentWeb
        from .yui_common import YAlignmentType
        return YAlignmentWeb(parent, horAlign=YAlignmentType.YAlignUnchanged, vertAlign=YAlignmentType.YAlignBegin)

    def createBottom(self, parent):
        from .backends.web import YAlignmentWeb
        from .yui_common import YAlignmentType
        return YAlignmentWeb(parent, horAlign=YAlignmentType.YAlignUnchanged, vertAlign=YAlignmentType.YAlignEnd)

    def createHCenter(self, parent):
        from .backends.web import YAlignmentWeb
        from .yui_common import YAlignmentType
        return YAlignmentWeb(parent, horAlign=YAlignmentType.YAlignCenter, vertAlign=YAlignmentType.YAlignUnchanged)

    def createVCenter(self, parent):
        from .backends.web import YAlignmentWeb
        from .yui_common import YAlignmentType
        return YAlignmentWeb(parent, horAlign=YAlignmentType.YAlignUnchanged, vertAlign=YAlignmentType.YAlignCenter)

    def createHVCenter(self, parent):
        from .backends.web import YAlignmentWeb
        from .yui_common import YAlignmentType
        return YAlignmentWeb(parent, horAlign=YAlignmentType.YAlignCenter, vertAlign=YAlignmentType.YAlignCenter)

    def createAlignment(self, parent, horAlignment, vertAlignment):
        from .backends.web import YAlignmentWeb
        return YAlignmentWeb(parent, horAlign=horAlignment, vertAlign=vertAlignment)

    def createMinWidth(self, parent, minWidth: int):
        from .backends.web import YAlignmentWeb
        a = YAlignmentWeb(parent)
        a.setMinWidth(int(minWidth))
        return a

    def createMinHeight(self, parent, minHeight: int):
        from .backends.web import YAlignmentWeb
        a = YAlignmentWeb(parent)
        a.setMinHeight(int(minHeight))
        return a

    def createMinSize(self, parent, minWidth: int, minHeight: int):
        from .backends.web import YAlignmentWeb
        a = YAlignmentWeb(parent)
        a.setMinSize(int(minWidth), int(minHeight))
        return a

    # --- Spacing ---
    
    def createSpacing(self, parent, dim: YUIDimension, stretchable: bool = False, size_px: int = 0):
        from .backends.web import YSpacingWeb
        return YSpacingWeb(parent, dim, stretchable, size_px)

    def createHStretch(self, parent):
        return self.createSpacing(parent, YUIDimension.Horizontal, stretchable=True)

    def createVStretch(self, parent):
        return self.createSpacing(parent, YUIDimension.Vertical, stretchable=True)

    def createHSpacing(self, parent, size_px: int = 8):
        return self.createSpacing(parent, YUIDimension.Horizontal, stretchable=False, size_px=size_px)

    def createVSpacing(self, parent, size_px: int = 16):
        return self.createSpacing(parent, YUIDimension.Vertical, stretchable=False, size_px=size_px)

    # --- Advanced Widgets ---
    
    def createTree(self, parent, label, multiselection=False, recursiveselection=False):
        from .backends.web import YTreeWeb
        return YTreeWeb(parent, label, multiselection, recursiveselection)

    def createTable(self, parent, header: YTableHeader, multiSelection: bool = False):
        from .backends.web import YTableWeb
        return YTableWeb(parent, header, multiSelection)

    def createRichText(self, parent, text: str = "", plainTextMode: bool = False):
        from .backends.web import YRichTextWeb
        return YRichTextWeb(parent, text, plainTextMode)

    def createMenuBar(self, parent):
        from .backends.web import YMenuBarWeb
        return YMenuBarWeb(parent)

    def createReplacePoint(self, parent):
        from .backends.web import YReplacePointWeb
        return YReplacePointWeb(parent)

    def createCheckBoxFrame(self, parent, label: str = "", checked: bool = False):
        from .backends.web import YCheckBoxFrameWeb
        return YCheckBoxFrameWeb(parent, label, checked)

    def createRadioButton(self, parent, label: str = "", isChecked: bool = False):
        from .backends.web import YRadioButtonWeb
        return YRadioButtonWeb(parent, label, isChecked)

    def createIntField(self, parent, label, minVal, maxVal, initialVal):
        from .backends.web import YIntFieldWeb
        return YIntFieldWeb(parent, label, minVal, maxVal, initialVal)

    def createMultiLineEdit(self, parent, label):
        from .backends.web import YMultiLineEditWeb
        return YMultiLineEditWeb(parent, label)

    def createImage(self, parent, imageFileName, fallBackName=None):
        from .backends.web import YImageWeb
        return YImageWeb(parent, imageFileName, fallBackName=fallBackName)

    def createDumbTab(self, parent):
        from .backends.web import YDumbTabWeb
        return YDumbTabWeb(parent)

    def createSlider(self, parent, label: str, minVal: int, maxVal: int, initialVal: int):
        from .backends.web import YSliderWeb
        return YSliderWeb(parent, label, minVal, maxVal, initialVal)

    def createDateField(self, parent, label):
        from .backends.web import YDateFieldWeb
        return YDateFieldWeb(parent, label)

    def createTimeField(self, parent, label):
        from .backends.web import YTimeFieldWeb
        return YTimeFieldWeb(parent, label)

    def createLogView(self, parent, label, visibleLines, storedLines=0):
        from .backends.web import YLogViewWeb
        return YLogViewWeb(parent, label, visibleLines, storedLines)

    def createPaned(self, parent, dimension: YUIDimension = YUIDimension.YD_HORIZ):
        from .backends.web import YPanedWeb
        return YPanedWeb(parent, dimension)
