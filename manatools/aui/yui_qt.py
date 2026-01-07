"""
Qt backend implementation for YUI
"""

import sys
from PySide6 import QtWidgets, QtCore, QtGui
import os
import logging
from .yui_common import *
from .backends.qt import *
from .backends.qt.commonqt import _resolve_icon

class YUIQt:
    def __init__(self):
        self._widget_factory = YWidgetFactoryQt()
        self._optional_widget_factory = None
        # Ensure QApplication exists
        self._qapp = QtWidgets.QApplication.instance()
        if not self._qapp:
            self._qapp = QtWidgets.QApplication(sys.argv)
        self._application = YApplicationQt()
        # logger for the backend manager
        try:
            self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        except Exception:
            self._logger = logging.getLogger("manatools.aui.qt.YUIQt")

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

class YApplicationQt:
    def __init__(self):
        self._application_title = "manatools Qt Application"
        self._product_name = "manatools AUI Qt"
        self._icon_base_path = None
        self._icon = "manatools"  # default icon name
        # cached QIcon resolved from _icon (None if not resolved)
        self._qt_icon = None
        try:
            self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        except Exception:
            self._logger = logging.getLogger("manatools.aui.qt.YApplicationQt")

    def iconBasePath(self):
        return self._icon_base_path
    
    def setIconBasePath(self, new_icon_base_path):
        self._icon_base_path = new_icon_base_path
    
    def setProductName(self, product_name):
        self._product_name = product_name
    
    def productName(self):
        return self._product_name
    
    def setApplicationTitle(self, title):
        """Set the application title."""
        self._application_title = title
        # also keep Qt's application name in sync so dialogs can read it without importing YUI
        try:
            app = QtWidgets.QApplication.instance()
            if app:
                app.setApplicationName(title)
                top_level_widgets = app.topLevelWidgets()

                for widget in top_level_widgets:
                    if isinstance(widget, QtWidgets.QMainWindow):
                        main_window = widget
                        main_window.setWindowTitle(title)
                        break
        except Exception:
            pass

    def setApplicationIcon(self, Icon):
        """Set application icon spec (theme name or path). Try to apply it to QApplication and active dialogs.

        If iconBasePath is set, icon is considered relative to that path and will force local file usage.
        """
        try:
            self._icon = Icon
        except Exception:
            self._icon = ""
        # resolve into a QIcon and cache
        try:
            self._qt_icon = _resolve_icon(self._icon)
        except Exception:
            self._qt_icon = None

        # apply to global QApplication
        try:
            app = QtWidgets.QApplication.instance()
            if app and self._qt_icon:
                try:
                    app.setWindowIcon(self._qt_icon)
                except Exception:
                    pass
        except Exception:
            pass

        # apply to any open YDialogQt windows (if backend used)
        try:
            # avoid importing the whole module if not available
            from . import yui as yui_mod
            # try to update dialogs known in YDialogQt._open_dialogs
            dlg_cls = getattr(yui_mod, "YDialogQt", None)
            if dlg_cls is None:
                # fallback to import local symbol if module structure different
                dlg_cls = globals().get("YDialogQt", None)
            if dlg_cls is not None:
                for dlg in getattr(dlg_cls, "_open_dialogs", []) or []:
                    try:
                        w = getattr(dlg, "_qwidget", None)
                        if w and self._qt_icon:
                            try:
                                w.setWindowIcon(self._qt_icon)
                            except Exception:
                                pass
                    except Exception:
                        pass
        except Exception:
            # best-effort; ignore failures
            pass

    def applicationTitle(self):
        """Get the application title."""
        return self._application_title

    def askForExistingDirectory(self, startDir: str, headline: str):
        """
        Prompt user to select an existing directory.

        Parameters:
        - startDir: initial folder to display (string, may be empty)
        - headline: explanatory text for the dialog

        Returns: selected directory path as string, or empty string if cancelled.
        """
        try:
            start = startDir or ""
            # Use QFileDialog static helper for convenience
            res = QtWidgets.QFileDialog.getExistingDirectory(None, headline or "Select Directory", start)
            return res or ""
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
            start = startWith or ""
            flt = filter if filter else "All files (*)"
            fn, _ = QtWidgets.QFileDialog.getOpenFileName(None, headline or "Open File", start, flt)
            return fn or ""
        except Exception:
            try:
                self._logger.exception("askForExistingFile failed")
            except Exception:
                pass
            return ""

    def askForSaveFileName(self, startWith: str, filter: str, headline: str):
        """
        Prompt user to choose a filename to save data.

        Parameters are as in `askForExistingFile`.

        Returns: selected filename as string, or empty string if cancelled.
        """
        try:
            start = startWith or ""
            flt = filter if filter else "All files (*)"
            fn, _ = QtWidgets.QFileDialog.getSaveFileName(None, headline or "Save File", start, flt)
            return fn or ""
        except Exception:
            try:
                self._logger.exception("askForSaveFileName failed")
            except Exception:
                pass
            return ""

    def setApplicationIcon(self, Icon):
        """Set the application title."""
        self._icon = Icon

    def applicationIcon(self):
        """Get the application icon."""
        return self._icon

class YWidgetFactoryQt:
    def __init__(self):
        pass
    
    def createMainDialog(self, color_mode=YDialogColorMode.YDialogNormalColor):
        return YDialogQt(YDialogType.YMainDialog, color_mode)
    
    def createPopupDialog(self, color_mode=YDialogColorMode.YDialogNormalColor):
        return YDialogQt(YDialogType.YPopupDialog, color_mode)
    
    def createVBox(self, parent):
        return YVBoxQt(parent)
    
    def createHBox(self, parent):
        return YHBoxQt(parent)
    
    def createPushButton(self, parent, label):
        return YPushButtonQt(parent, label)
    
    def createLabel(self, parent, text, isHeading=False, isOutputField=False):
        return YLabelQt(parent, text, isHeading, isOutputField)
    
    def createHeading(self, parent, label):
        return YLabelQt(parent, label, isHeading=True)
    
    def createInputField(self, parent, label, password_mode=False):
        return YInputFieldQt(parent, label, password_mode)

    def createMultiLineEdit(self, parent, label):
        return YMultiLineEditQt(parent, label)

    def createIntField(self, parent, label, minVal, maxVal, initialVal):
        return YIntFieldQt(parent, label, minVal, maxVal, initialVal)
    
    def createCheckBox(self, parent, label, is_checked=False):
        return YCheckBoxQt(parent, label, is_checked)
    
    def createPasswordField(self, parent, label):
        return YInputFieldQt(parent, label, password_mode=True)
    
    def createComboBox(self, parent, label, editable=False):
        return YComboBoxQt(parent, label, editable)
    
    def createSelectionBox(self, parent, label):
        return YSelectionBoxQt(parent, label)

    #Multi-selection box variant
    def createMultiSelectionBox(self, parent, label):
        return YSelectionBoxQt(parent, label, multi_selection=True)

    def createProgressBar(self, parent, label, max_value=100):
        return YProgressBarQt(parent, label, max_value)
    
    def createComboBox(self, parent, label, editable=False):
        return YComboBoxQt(parent, label, editable)
    
    # Alignment helpers
    def createLeft(self, parent):
        return YAlignmentQt(parent, horAlign=YAlignmentType.YAlignBegin, vertAlign=YAlignmentType.YAlignUnchanged)

    def createRight(self, parent):
        return YAlignmentQt(parent, horAlign=YAlignmentType.YAlignEnd, vertAlign=YAlignmentType.YAlignUnchanged)

    def createTop(self, parent):
        return YAlignmentQt(parent, horAlign=YAlignmentType.YAlignUnchanged, vertAlign=YAlignmentType.YAlignBegin)

    def createBottom(self, parent):
        return YAlignmentQt(parent, horAlign=YAlignmentType.YAlignUnchanged, vertAlign=YAlignmentType.YAlignEnd)

    def createHCenter(self, parent):
        return YAlignmentQt(parent, horAlign=YAlignmentType.YAlignCenter, vertAlign=YAlignmentType.YAlignUnchanged)

    def createVCenter(self, parent):
        return YAlignmentQt(parent, horAlign=YAlignmentType.YAlignUnchanged, vertAlign=YAlignmentType.YAlignCenter)

    def createHVCenter(self, parent):
        return YAlignmentQt(parent, horAlign=YAlignmentType.YAlignCenter, vertAlign=YAlignmentType.YAlignCenter)

    def createAlignment(self, parent, horAlignment: YAlignmentType, vertAlignment: YAlignmentType):
        """Create a generic YAlignment using YAlignmentType enums (or compatible specs)."""
        return YAlignmentQt(parent, horAlign=horAlignment, vertAlign=vertAlignment)

    def createMinWidth(self, parent, minWidth: int):
        a = YAlignmentQt(parent)
        try:
            a.setMinWidth(int(minWidth))
        except Exception:
            pass
        return a

    def createMinHeight(self, parent, minHeight: int):
        a = YAlignmentQt(parent)
        try:
            a.setMinHeight(int(minHeight))
        except Exception:
            pass
        return a

    def createMinSize(self, parent, minWidth: int, minHeight: int):
        a = YAlignmentQt(parent)
        try:
            a.setMinSize(int(minWidth), int(minHeight))
        except Exception:
            pass
        return a
    
    def createTree(self, parent, label, multiselection=False, recursiveselection = False):
        """Create a Tree widget."""
        return YTreeQt(parent, label, multiselection, recursiveselection)
    
    def createFrame(self, parent, label: str=""):
        """Create a Frame widget."""
        return YFrameQt(parent, label)
    
    def createCheckBoxFrame(self, parent, label: str = "", checked: bool = False):
        """Create a CheckBox Frame widget."""
        return YCheckBoxFrameQt(parent, label, checked)

    def createRadioButton(self, parent, label:str = "", isChecked:bool = False):    
        """Create a Radio Button widget."""
        return YRadioButtonQt(parent, label, isChecked)
    
    def createTable(self, parent, header: YTableHeader, multiSelection: bool = False):
        """Create a Table widget."""
        return YTableQt(parent, header, multiSelection)   

    def createRichText(self, parent, text: str = "", plainTextMode: bool = False):
        """Create a RichText widget (Qt backend)."""
        return YRichTextQt(parent, text, plainTextMode)

    def createMenuBar(self, parent):
        """Create a MenuBar widget (Qt backend)."""
        return YMenuBarQt(parent)

    def createReplacePoint(self, parent):
        """Create a ReplacePoint widget (Qt backend)."""
        return YReplacePointQt(parent)

    def createDumbTab(self, parent):
        """Create a DumbTab (tab bar with single content area, Qt backend)."""
        return YDumbTabQt(parent)

    def createSpacing(self, parent, dim: YUIDimension, stretchable: bool = False, size_px: int = 0):
        """Create a Spacing/Stretch widget.

        - `dim`: primary dimension for spacing (YUIDimension)
        - `stretchable`: expand in primary dimension when True (minimum size = `size`)
        - `size_px`: spacing size in pixels (device units, integer)
        """
        return YSpacingQt(parent, dim, stretchable, size_px)

    def createImage(self, parent, imageFileName):
        """Create an image widget."""
        return YImageQt(parent, imageFileName)

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
        """Create a Slider widget (Qt backend)."""
        return YSliderQt(parent, label, minVal, maxVal, initialVal)
    
    def createVSpacing(self, parent, size_px: int = 16):
        """Create a Vertical Spacing widget."""
        return self.createSpacing(parent, YUIDimension.Vertical, stretchable=False, size_px=size_px)