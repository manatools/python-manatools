"""
Qt backend implementation for YUI
"""

import sys
from PySide6 import QtWidgets, QtCore, QtGui
import os
from .yui_common import *
from .backends.qt import *

class YUIQt:
    def __init__(self):
        self._widget_factory = YWidgetFactoryQt()
        self._optional_widget_factory = None
        # Ensure QApplication exists
        self._qapp = QtWidgets.QApplication.instance()
        if not self._qapp:
            self._qapp = QtWidgets.QApplication(sys.argv)
        self._application = YApplicationQt()

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
        self._icon = ""
        # cached QIcon resolved from _icon (None if not resolved)
        self._qt_icon = None

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

    def _resolve_qicon(self, icon_spec):
        """Resolve icon_spec (path or theme name) into a QtGui.QIcon or None.
        If iconBasePath is set, prefer that as absolute path base.
        """
        if not icon_spec:
            return None
        # if we have a base path and the spec is not absolute, try that first
        try:
            if self._icon_base_path:
                cand = icon_spec
                if not os.path.isabs(cand):
                    cand = os.path.join(self._icon_base_path, icon_spec)
                if os.path.exists(cand):
                    return QtGui.QIcon(cand)
            # if icon_spec looks like an absolute path, try it
            if os.path.isabs(icon_spec) and os.path.exists(icon_spec):
                return QtGui.QIcon(icon_spec)
        except Exception:
            pass
        # fallback to theme lookup
        try:
            theme_icon = QtGui.QIcon.fromTheme(icon_spec)
            if not theme_icon.isNull():
                return theme_icon
        except Exception:
            pass
        return None

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
            self._qt_icon = self._resolve_qicon(self._icon)
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
    
    def createCheckBox(self, parent, label, is_checked=False):
        return YCheckBoxQt(parent, label, is_checked)
    
    def createPasswordField(self, parent, label):
        return YInputFieldQt(parent, label, password_mode=True)
    
    def createComboBox(self, parent, label, editable=False):
        return YComboBoxQt(parent, label, editable)
    
    def createSelectionBox(self, parent, label):
        return YSelectionBoxQt(parent, label)
    
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