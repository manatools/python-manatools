"""
Web backend implementation for YUI

This backend renders widgets as HTML and serves them via HTTP.
User interaction is handled via WebSocket for real-time communication.
"""

import logging
from .yui_common import YDialogType, YDialogColorMode, YUIDimension, YTableHeader


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

    def askForExistingDirectory(self, startDir: str, headline: str):
        """Not supported in web backend - returns empty string."""
        self._logger.warning("askForExistingDirectory not supported in web backend")
        return ""

    def askForExistingFile(self, startWith: str, filter: str, headline: str):
        """Not supported in web backend - returns empty string."""
        self._logger.warning("askForExistingFile not supported in web backend")
        return ""

    def askForSaveFileName(self, startWith: str, filter: str, headline: str):
        """Not supported in web backend - returns empty string."""
        self._logger.warning("askForSaveFileName not supported in web backend")
        return ""


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

    def createImage(self, parent, imageFileName):
        from .backends.web import YImageWeb
        return YImageWeb(parent, imageFileName)

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
