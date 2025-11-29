"""
Qt backend implementation for YUI
"""

import sys
from PySide6 import QtWidgets, QtCore, QtGui
import os
from .yui_common import *

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
        self._product_name = "manatools YUI Qt"
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
    # Alignment helpers
    def createLeft(self, parent):
        return YAlignmentQt(parent, horAlign=YAlignmentType.YAlignBegin,  vertAlign=YAlignmentType.YAlignUnchanged)

    def createRight(self, parent):
        return YAlignmentQt(parent, horAlign=YAlignmentType.YAlignEnd, vertAlign=YAlignmentType.YAlignUnchanged)

    def createTop(self, parent):
        return YAlignmentQt(parent, horAlign=YAlignmentType.YAlignUnchanged,   vertAlign=YAlignmentType.YAlignBegin)

    def createBottom(self, parent):
        return YAlignmentQt(parent, horAlign=YAlignmentType.YAlignUnchanged,   vertAlign=YAlignmentType.YAlignEnd)

    def createHCenter(self, parent):
        return YAlignmentQt(parent, horAlign=YAlignmentType.YAlignCenter, vertAlign=YAlignmentType.YAlignUnchanged)

    def createVCenter(self, parent):
        return YAlignmentQt(parent, horAlign=YAlignmentType.YAlignUnchanged,      vertAlign=YAlignmentType.YAlignCenter)

    def createHVCenter(self, parent):
        return YAlignmentQt(parent, horAlign=YAlignmentType.YAlignCenter, vertAlign=YAlignmentType.YAlignCenter)

    def createAlignment(self, parent, horAlignment: YAlignmentType, vertAlignment: YAlignmentType):
        """Create a generic YAlignment using YAlignmentType enums (or compatible specs)."""
        return YAlignmentQt(parent, horAlign=horAlignment, vertAlign=vertAlignment)
    
    def createTree(self, parent, label, multiselection=False, recursiveselection = False):
        """Create a Tree widget."""
        return YTreeQt(parent, label, multiselection, recursiveselection)


# Qt Widget Implementations
class YDialogQt(YSingleChildContainerWidget):
    _open_dialogs = []
    
    def __init__(self, dialog_type=YDialogType.YMainDialog, color_mode=YDialogColorMode.YDialogNormalColor):
        super().__init__()
        self._dialog_type = dialog_type
        self._color_mode = color_mode
        self._is_open = False
        self._qwidget = None
        self._event_result = None
        self._qt_event_loop = None
        YDialogQt._open_dialogs.append(self)
    
    def widgetClass(self):
        return "YDialog"
    
    @staticmethod
    def currentDialog(doThrow=True):
        '''Return the currently open dialog (topmost), or raise if none.'''
        open_dialog = YDialogQt._open_dialogs[-1] if YDialogQt._open_dialogs else None
        if not open_dialog and doThrow:
            raise YUINoDialogException("No dialog is currently open")
        return open_dialog
    
    @staticmethod
    def topmostDialog(doThrow=True):
        ''' same as currentDialog '''
        return YDialogQt.currentDialog(doThrow=doThrow)
    
    def isTopmostDialog(self):
        '''Return whether this dialog is the topmost open dialog.'''
        return YDialogQt._open_dialogs[-1] == self if YDialogQt._open_dialogs else False

    def open(self):
        """
        Finalize and show the dialog in a non-blocking way.

        Matches libyui semantics: open() should only finalize and make visible.
        If the application expects blocking behavior it should call waitForEvent()
        which will start a nested event loop as required.
        """
        if not self._is_open:
            if not self._qwidget:
                self._create_backend_widget()
            
            self._qwidget.show()
            self._is_open = True       
     
    def isOpen(self):
         return self._is_open
    
    def destroy(self, doThrow=True):
        if self._qwidget:
            self._qwidget.close()
            self._qwidget = None
        self._is_open = False
        if self in YDialogQt._open_dialogs:
            YDialogQt._open_dialogs.remove(self)
        return True
    
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
        self._qwidget = QtWidgets.QMainWindow()
        # Determine window title:from YApplicationQt instance stored on the YUI backend
        title = "Manatools YUI Qt Dialog"
        
        try:
            from . import yui as yui_mod
            appobj = None
            # YUI._backend may hold the backend instance (YUIQt)
            backend = getattr(yui_mod.YUI, "_backend", None)
            if backend:
                if hasattr(backend, "application"):
                    appobj = backend.application()
            # fallback: YUI._instance might be set and expose application/yApp
            if not appobj:
                inst = getattr(yui_mod.YUI, "_instance", None)
                if inst:
                    if hasattr(inst, "application"):
                        appobj = inst.application()
            if appobj and hasattr(appobj, "applicationTitle"):
                atitle = appobj.applicationTitle()
                if atitle:
                    title = atitle
            # try to obtain a resolved QIcon from the application backend if available
            app_qicon = None
            if appobj:
                # prefer cached Qt icon if set by setApplicationIcon
                app_qicon = getattr(appobj, "_qt_icon", None)
                # otherwise try to resolve applicationIcon string on the fly
                if not app_qicon:
                    try:
                        icon_spec = appobj.applicationIcon()
                        if icon_spec:
                            # use the application's iconBasePath if present
                            base = getattr(appobj, "_icon_base_path", None)
                            if base and not os.path.isabs(icon_spec):
                                p = os.path.join(base, icon_spec)
                                if os.path.exists(p):
                                    app_qicon = QtGui.QIcon(p)
                            if not app_qicon:
                                q = QtGui.QIcon.fromTheme(icon_spec)
                                if not q.isNull():
                                    app_qicon = q
                    except Exception:
                        pass
            # if we have a qicon, set it on the QApplication and the new window
            if app_qicon:
                try:
                    qapp = QtWidgets.QApplication.instance()
                    if qapp:
                        qapp.setWindowIcon(app_qicon)
                except Exception:
                    pass
            # store resolved qicon locally to apply to this window
            _resolved_qicon = app_qicon
        except Exception:
            # ignore and keep default
            _resolved_qicon = None

        self._qwidget.setWindowTitle(title)
        try:
            if _resolved_qicon:
                self._qwidget.setWindowIcon(_resolved_qicon)
        except Exception:
            pass
        self._qwidget.resize(600, 400)

        central_widget = QtWidgets.QWidget()
        self._qwidget.setCentralWidget(central_widget)
        
        if self._child:
            layout = QtWidgets.QVBoxLayout(central_widget)
            layout.addWidget(self._child.get_backend_widget())
        
        self._backend_widget = self._qwidget
        self._qwidget.closeEvent = self._on_close_event
    
    def _set_backend_enabled(self, enabled):
        """Enable/disable the dialog window and propagate to logical child widgets."""
        try:
            if getattr(self, "_qwidget", None) is not None:
                try:
                    self._qwidget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass
        # propagate logical enabled state to contained YWidget(s)
        try:
            if getattr(self, "_child", None):
                try:
                    self._child.setEnabled(enabled)
                except Exception:
                    pass
            else:
                for c in list(getattr(self, "_children", []) or []):
                    try:
                        c.setEnabled(enabled)
                    except Exception:
                        pass
        except Exception:
            pass

    def _on_close_event(self, event):
        # Post a cancel event so waitForEvent returns a YCancelEvent when the user
        # closes the window with the window manager 'X' button.
        try:
            self._post_event(YCancelEvent())
        except Exception:
            pass
        # Ensure dialog is destroyed and accept the close
        self.destroy()
        event.accept()
    
    def _post_event(self, event):
        """Internal: post an event to this dialog and quit local event loop if running."""
        self._event_result = event
        if self._qt_event_loop is not None and self._qt_event_loop.isRunning():
            self._qt_event_loop.quit()

    def waitForEvent(self, timeout_millisec=0):
        """
        Ensure dialog is finalized/open, then run a nested Qt QEventLoop until an
        event is posted or timeout occurs. Returns a YEvent (YWidgetEvent, YTimeoutEvent, ...).

        If the application called open() previously this will just block until an event.
        If open() was not called, it will finalize and show the dialog here (so creation
        followed by immediate waitForEvent behaves like libyui).
        """
        # Ensure dialog is created and visible (finalize if needed)
        if not self._qwidget:
            self.open()

        # give Qt a chance to process pending show/layout events
        app = QtWidgets.QApplication.instance()
        if app:
            app.processEvents()

        self._event_result = None
        loop = QtCore.QEventLoop()
        self._qt_event_loop = loop

        timer = None
        if timeout_millisec and timeout_millisec > 0:
            timer = QtCore.QTimer()
            timer.setSingleShot(True)
            def on_timeout():
                # post timeout event and quit
                self._event_result = YTimeoutEvent()
                if loop.isRunning():
                    loop.quit()
            timer.timeout.connect(on_timeout)
            timer.start(timeout_millisec)

        # PySide6 / Qt6 uses exec()
        loop.exec()

        # cleanup
        if timer and timer.isActive():
            timer.stop()
        self._qt_event_loop = None
        return self._event_result if self._event_result is not None else YEvent()


class YVBoxQt(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def widgetClass(self):
        return "YVBox"

    # Returns the stretchability of the layout box:
    #  * The layout box is stretchable if one of the children is stretchable in
    #  * this dimension or if one of the child widgets has a layout weight in
    #  * this dimension.
    def stretchable(self, dim):
        for child in self._children:
            widget = child.get_backend_widget()
            expand = bool(child.stretchable(dim))
            weight = bool(child.weight(dim))
            if expand or weight:
                return True
        # No child is stretchable in this dimension
        return False

    def _create_backend_widget(self):
        self._backend_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self._backend_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        for child in self._children:
            widget = child.get_backend_widget()
            expand = 1 if child.stretchable(YUIDimension.YD_VERT) else 0

            # If the child requests horizontal stretch, set its QSizePolicy to Expanding
            try:
                if expand == 1:
                    sp = widget.sizePolicy()
                    try:
                        sp.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Expanding)
                    except Exception:
                        try:
                            sp.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
                        except Exception:
                            pass
                    widget.setSizePolicy(sp)
            except Exception:
                pass



            print(  f"YVBoxQt: adding child {child.widgetClass()} expand={expand}" ) #TODO remove debug
            layout.addWidget(widget, stretch=expand)

    def _set_backend_enabled(self, enabled):
        """Enable/disable the VBox container and propagate to children."""
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
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

class YHBoxQt(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def widgetClass(self):
        return "YHBox"

    # Returns the stretchability of the layout box:
    #  * The layout box is stretchable if one of the children is stretchable in
    #  * this dimension or if one of the child widgets has a layout weight in
    #  * this dimension.
    def stretchable(self, dim):
        for child in self._children:
            widget = child.get_backend_widget()
            expand = bool(child.stretchable(dim))
            weight = bool(child.weight(dim))
            if expand or weight:
                return True
        # No child is stretchable in this dimension
        return False

    def _create_backend_widget(self):
        self._backend_widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(self._backend_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        for child in self._children:
            widget = child.get_backend_widget()
            expand = 1 if child.stretchable(YUIDimension.YD_HORIZ) else 0

            # If the child requests horizontal stretch, set its QSizePolicy to Expanding
            try:
                if expand == 1:
                    sp = widget.sizePolicy()
                    try:
                        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Expanding)
                    except Exception:
                        try:
                            sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
                        except Exception:
                            pass
                    widget.setSizePolicy(sp)
            except Exception:
                pass
            print(  f"YHBoxQt: adding child {child.widgetClass()} expand={expand}" ) #TODO remove debug
            layout.addWidget(widget, stretch=expand)

    def _set_backend_enabled(self, enabled):
        """Enable/disable the HBox container and propagate to children."""
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
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

class YLabelQt(YWidget):
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
            self._backend_widget.setText(new_text)
    
    def _create_backend_widget(self):
        self._backend_widget = QtWidgets.QLabel(self._text)
        if self._is_heading:
            font = self._backend_widget.font()
            font.setBold(True)
            font.setPointSize(font.pointSize() + 2)
            self._backend_widget.setFont(font)

    def _set_backend_enabled(self, enabled):
        """Enable/disable the QLabel backend."""
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass

class YInputFieldQt(YWidget):
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
            self._entry_widget.setText(text)
    
    def label(self):
        return self._label
    
    def _create_backend_widget(self):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if self._label:
            label = QtWidgets.QLabel(self._label)
            layout.addWidget(label)
        
        if self._password_mode:
            entry = QtWidgets.QLineEdit()
            entry.setEchoMode(QtWidgets.QLineEdit.Password)
        else:
            entry = QtWidgets.QLineEdit()
        
        entry.setText(self._value)
        entry.textChanged.connect(self._on_text_changed)
        layout.addWidget(entry)
        
        self._backend_widget = container
        self._entry_widget = entry

    def _set_backend_enabled(self, enabled):
        """Enable/disable the input field: entry and container."""
        try:
            if getattr(self, "_entry_widget", None) is not None:
                try:
                    self._entry_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass

    def _on_text_changed(self, text):
        self._value = text

class YPushButtonQt(YWidget):
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
            self._backend_widget.setText(label)
    
    def _create_backend_widget(self):
        self._backend_widget = QtWidgets.QPushButton(self._label)
        # Set size policy to prevent unwanted expansion
        try:
            try:
                sp = self._backend_widget.sizePolicy()
                # PySide6 may expect enum class; try both styles defensively
                try:
                    sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Minimum)
                except Exception:
                    try:
                        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Minimum)
                    except Exception:
                        pass
                self._backend_widget.setSizePolicy(sp)
            except Exception:
                try:
                    # fallback: set using convenience form (two args)
                    self._backend_widget.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
                except Exception:
                    pass
        except Exception:
             pass
        self._backend_widget.clicked.connect(self._on_clicked)

    def _set_backend_enabled(self, enabled):
        """Enable/disable the QPushButton backend."""
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass

    def _on_clicked(self):
        # Post a YWidgetEvent to the containing dialog (walk parents)
        dlg = self.findDialog()
        if dlg is not None:
            dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
        else:
            # fallback logging for now
            print(f"Button clicked (no dialog found): {self._label}")

class YCheckBoxQt(YWidget):
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
                # avoid emitting signals while programmatically changing state
                self._backend_widget.blockSignals(True)
                self._backend_widget.setChecked(checked)
            finally:
                try:
                    self._backend_widget.blockSignals(False)
                except Exception:
                    pass
    
    def label(self):
        return self._label
    
    def _create_backend_widget(self):
        self._backend_widget = QtWidgets.QCheckBox(self._label)
        self._backend_widget.setChecked(self._is_checked)
        self._backend_widget.stateChanged.connect(self._on_state_changed)

    def _set_backend_enabled(self, enabled):
        """Enable/disable the QCheckBox backend."""
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass

    def _on_state_changed(self, state):
        # Update internal state
        # state is QtCore.Qt.CheckState (Unchecked=0, PartiallyChecked=1, Checked=2)
        self._is_checked = (QtCore.Qt.CheckState(state) == QtCore.Qt.CheckState.Checked)

        if self.notify():
            # Post a YWidgetEvent to the containing dialog
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
            else:
                print(f"CheckBox state changed (no dialog found): {self._label} = {self._is_checked}")

class YComboBoxQt(YSelectionWidget):
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
        self._value = text
        if hasattr(self, '_combo_widget') and self._combo_widget:
            index = self._combo_widget.findText(text)
            if index >= 0:
                self._combo_widget.setCurrentIndex(index)
            elif self._editable:
                self._combo_widget.setEditText(text)
        # update selected_items to keep internal state consistent
        self._selected_items = []
        for item in self._items:
            if item.label() == text:
                self._selected_items.append(item)
                break
    
    def editable(self):
        return self._editable
    
    def _create_backend_widget(self):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if self._label:
            label = QtWidgets.QLabel(self._label)
            layout.addWidget(label)
        
        if self._editable:
            combo = QtWidgets.QComboBox()
            combo.setEditable(True)
        else:
            combo = QtWidgets.QComboBox()
        
        # Add items to combo box
        for item in self._items:
            combo.addItem(item.label())
        
        combo.currentTextChanged.connect(self._on_text_changed)
        # also handle index change (safer for some input methods)
        combo.currentIndexChanged.connect(lambda idx: self._on_text_changed(combo.currentText()))
        layout.addWidget(combo)
        
        self._backend_widget = container
        self._combo_widget = combo

    def _set_backend_enabled(self, enabled):
        """Enable/disable the combobox and its container."""
        try:
            if getattr(self, "_combo_widget", None) is not None:
                try:
                    self._combo_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass

    def _on_text_changed(self, text):
        self._value = text
        # Update selected items
        self._selected_items = []
        for item in self._items:
            if item.label() == text:
                self._selected_items.append(item)
                break
        if self.notify():
            # Post selection-changed event to containing dialog
            try:
                dlg = self.findDialog()
                if dlg is not None:
                    dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
            except Exception:
                pass

class YSelectionBoxQt(YSelectionWidget):
    def __init__(self, parent=None, label=""):
        super().__init__(parent)
        self._label = label
        self._value = ""
        self._selected_items = []
        self._multi_selection = False
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)
    
    def widgetClass(self):
        return "YSelectionBox"
    
    def value(self):
        return self._value
    
    def setValue(self, text):
        self._value = text
        if hasattr(self, '_list_widget') and self._list_widget:
            # Find and select the item with matching text
            for i in range(self._list_widget.count()):
                item = self._list_widget.item(i)
                if item.text() == text:
                    self._list_widget.setCurrentItem(item)
                    break
        # Update selected_items to keep internal state consistent
        self._selected_items = []
        for item in self._items:
            if item.label() == text:
                self._selected_items.append(item)
                break
    
    def label(self):
        return self._label
    
    def selectedItems(self):
        """Get list of selected items"""
        return self._selected_items
    
    def selectItem(self, item, selected=True):
        """Select or deselect a specific item"""
        if hasattr(self, '_list_widget') and self._list_widget:
            for i in range(self._list_widget.count()):
                list_item = self._list_widget.item(i)
                if list_item.text() == item.label():
                    if selected:
                        self._list_widget.setCurrentItem(list_item)
                        if item not in self._selected_items:
                            self._selected_items.append(item)
                    else:
                        if item in self._selected_items:
                            self._selected_items.remove(item)
                    break

    def setMultiSelection(self, enabled):
        """Enable or disable multi-selection."""
        self._multi_selection = bool(enabled)
        if hasattr(self, '_list_widget') and self._list_widget:
            mode = QtWidgets.QAbstractItemView.MultiSelection if self._multi_selection else QtWidgets.QAbstractItemView.SingleSelection
            self._list_widget.setSelectionMode(mode)
            # if disabling multi-selection, collapse to the first selected item
            if not self._multi_selection:
                selected = self._list_widget.selectedItems()
                if len(selected) > 1:
                    first = selected[0]
                    self._list_widget.clearSelection()
                    first.setSelected(True)
                    # update internal state to reflect change
                    self._on_selection_changed()

    def multiSelection(self):
        """Return whether multi-selection is enabled."""
        return bool(self._multi_selection)
    
    def _create_backend_widget(self):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if self._label:
            label = QtWidgets.QLabel(self._label)
            layout.addWidget(label)
        
        list_widget = QtWidgets.QListWidget()
        mode = QtWidgets.QAbstractItemView.MultiSelection if self._multi_selection else QtWidgets.QAbstractItemView.SingleSelection
        list_widget.setSelectionMode(mode)
        
        # Add items to list widget
        for item in self._items:
            list_widget.addItem(item.label())
        
        list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(list_widget)
        
        self._backend_widget = container
        self._list_widget = list_widget

    def _set_backend_enabled(self, enabled):
        """Enable/disable the selection box and its list widget; propagate where applicable."""
        try:
            if getattr(self, "_list_widget", None) is not None:
                try:
                    self._list_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass

    def _on_selection_changed(self):
        """Handle selection change in the list widget"""
        if hasattr(self, '_list_widget') and self._list_widget:
            # Update selected items
            self._selected_items = []
            selected_indices = [index.row() for index in self._list_widget.selectedIndexes()]
            
            for idx in selected_indices:
                if idx < len(self._items):
                    self._selected_items.append(self._items[idx])
            
            # Update value to first selected item
            if self._selected_items:
                self._value = self._selected_items[0].label()
            
            # Post selection-changed event to containing dialog
            try:
                if self.notify():
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
            except Exception:
                pass

class YAlignmentQt(YSingleChildContainerWidget):
    """
    Single-child alignment container for Qt6. Uses a QWidget + QGridLayout,
    applying Qt.Alignment flags to the child. The container expands along
    axes needed by Right/HCenter/VCenter/HVCenter to allow alignment.
    """
    def __init__(self, parent=None, horAlign: YAlignmentType=YAlignmentType.YAlignUnchanged, vertAlign: YAlignmentType=YAlignmentType.YAlignUnchanged):
        super().__init__(parent)
        self._halign_spec = horAlign
        self._valign_spec = vertAlign
        self._backend_widget = None
        self._layout = None

    def widgetClass(self):
        return "YAlignment"

    def _to_qt_halign(self):
        """Convert Horizontal YAlignmentType to QtCore.Qt.AlignmentFlag or None."""        
        if self._halign_spec:
            if self._halign_spec == YAlignmentType.YAlignBegin:
                return QtCore.Qt.AlignmentFlag.AlignLeft
            if self._halign_spec == YAlignmentType.YAlignCenter:
                return QtCore.Qt.AlignmentFlag.AlignHCenter
            if self._halign_spec == YAlignmentType.YAlignEnd:
                return QtCore.Qt.AlignmentFlag.AlignRight
        return None
    
    def _to_qt_valign(self):
        """Convert Vertical YAlignmentType to QtCore.Qt.AlignmentFlag or None."""        
        if self._valign_spec:
            if self._valign_spec == YAlignmentType.YAlignBegin:
                return QtCore.Qt.AlignmentFlag.AlignTop
            if self._valign_spec == YAlignmentType.YAlignCenter:
                return QtCore.Qt.AlignmentFlag.AlignVCenter
            if self._valign_spec == YAlignmentType.YAlignEnd:
                return QtCore.Qt.AlignmentFlag.AlignBottom
        return None


    def stretchable(self, dim: YUIDimension):
        ''' Returns the stretchability of the layout box:
          * The layout box is stretchable if the alignment spec requests expansion
          * (Right/HCenter/HVCenter for horizontal, VCenter/HVCenter for vertical)
          * OR if the child itself requests stretchability or has a layout weight.
        '''
        # Expand if alignment spec requests it
        try:
            if dim == YUIDimension.YD_HORIZ:
                if self._halign_spec in (YAlignmentType.YAlignEnd, YAlignmentType.YAlignCenter):
                    return True
            if dim == YUIDimension.YD_VERT:
                if self._valign_spec in (YAlignmentType.YAlignCenter,):
                    return True
        except Exception:
            pass

        # Otherwise honor child's own stretchability/weight
        try:
            if self._child:
                expand = bool(self._child.stretchable(dim))
                weight = bool(self._child.weight(dim))
                if expand or weight:
                    return True
        except Exception:
            pass
        return False

    def setAlignment(self, horAlign: YAlignmentType=YAlignmentType.YAlignUnchanged, vertAlign: YAlignmentType=YAlignmentType.YAlignUnchanged):
        self._halign_spec = horAlign
        self._valign_spec = vertAlign
        self._reapply_alignment()

    def _reapply_alignment(self):
        if not (self._layout and self._child):
            return
        try:
            w = self._child.get_backend_widget()
            if w:
                self._layout.removeWidget(w)
                flags = QtCore.Qt.AlignmentFlag(0)
                ha = self._to_qt_halign()
                va = self._to_qt_valign()
                if ha:
                    flags |= ha
                if va:
                    flags |= va
                self._layout.addWidget(w, 0, 0, flags)
        except Exception:
            pass

    def addChild(self, child):
        try:
            super().addChild(child)
        except Exception:
            self._child = child
        if self._backend_widget:
            self._attach_child_backend()

    def setChild(self, child):
        try:
            super().setChild(child)
        except Exception:
            self._child = child
        if self._backend_widget:
            self._attach_child_backend()

    def _attach_child_backend(self):
        if not (self._backend_widget and self._layout and self._child):
            return
        try:
            w = self._child.get_backend_widget()
            if w:
                # clear previous
                try:
                    self._layout.removeWidget(w)
                except Exception:
                    pass
                flags = QtCore.Qt.AlignmentFlag(0)
                ha = self._to_qt_halign()
                va = self._to_qt_valign()
                if ha:
                    flags |= ha
                if va:
                    flags |= va
                # If the child requests horizontal stretch, set its QSizePolicy to Expanding
                try:
                    if self._child and self._child.stretchable(YUIDimension.YD_HORIZ):
                        sp = w.sizePolicy()
                        try:
                            sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Expanding)
                        except Exception:
                            try:
                                sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
                            except Exception:
                                pass
                        w.setSizePolicy(sp)
                    # If child requests vertical stretch, set vertical policy
                    if self._child and self._child.stretchable(YUIDimension.YD_VERT):
                        sp = w.sizePolicy()
                        try:
                            sp.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Expanding)
                        except Exception:
                            try:
                                sp.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
                            except Exception:
                                pass
                        w.setSizePolicy(sp)
                except Exception:
                    pass
                self._layout.addWidget(w, 0, 0, flags)
        except Exception:
            pass

    def _create_backend_widget(self):
        container = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)

        # Size policy: expand along axes needed for alignment to work
        sp = container.sizePolicy()
        try: 
            sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Expanding if self.stretchable(YUIDimension.YD_HORIZ)
                                   else QtWidgets.QSizePolicy.Policy.Fixed)
            sp.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Expanding if self.stretchable(YUIDimension.YD_VERT)
                                 else QtWidgets.QSizePolicy.Policy.Fixed)
        except Exception:
            pass
        container.setSizePolicy(sp)

        self._backend_widget = container
        self._layout = grid

        if getattr(self, "_child", None):
            self._attach_child_backend()

    def _set_backend_enabled(self, enabled):
        """Enable/disable the alignment container and propagate to its logical child."""
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass
        # propagate to logical child
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

class YTreeQt(YSelectionWidget):
    """
    Qt backend for YTree (based on YTree.h semantics).

    - Uses QTreeWidget to display hierarchical items stored in self._items.
    - Supports multiSelection and immediateMode.
    - Rebuild tree from internal items with rebuildTree().
    - currentItem() returns the YTreeItem wrapper for the focused/selected QTreeWidgetItem.
    - activate() simulates user activation of the current item (posts an Activated event).
    """
    def __init__(self, parent=None, label="", multiSelection=False, recursiveSelection=False):
        super().__init__(parent)
        self._label = label
        self._multi = bool(multiSelection)
        self._recursive = bool(recursiveSelection)
        self._immediate = False
        self._backend_widget = None
        self._tree_widget = None
        # mappings between QTreeWidgetItem and logical YTreeItem (python objects in self._items)
        self._qitem_to_item = {}
        self._item_to_qitem = {}

    def widgetClass(self):
        return "YTree"

    def _create_backend_widget(self):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if self._label:
            lbl = QtWidgets.QLabel(self._label)
            layout.addWidget(lbl)

        tree = QtWidgets.QTreeWidget()
        tree.setHeaderHidden(True)
        mode = QtWidgets.QAbstractItemView.MultiSelection if self._multi else QtWidgets.QAbstractItemView.SingleSelection
        tree.setSelectionMode(mode)
        tree.itemSelectionChanged.connect(self._on_selection_changed)
        tree.itemActivated.connect(self._on_item_activated)

        layout.addWidget(tree)
        self._backend_widget = container
        self._tree_widget = tree

        # populate if items already present
        try:
            self.rebuildTree()
        except Exception:
            pass

    def rebuildTree(self):
        """Rebuild the QTreeWidget from self._items (calls helper recursively)."""
        if self._tree_widget is None:
            # ensure backend exists
            self._create_backend_widget()
        # clear existing
        self._qitem_to_item.clear()
        self._item_to_qitem.clear()
        self._tree_widget.clear()

        def _add_recursive(parent_qitem, item):
            # item expected to provide label() and possibly children() iterable
            text = ""
            try:
                text = item.label()
            except Exception:
                try:
                    text = str(item)
                except Exception:
                    text = ""
            qitem = QtWidgets.QTreeWidgetItem([text])
            # preserve mapping
            self._qitem_to_item[qitem] = item
            self._item_to_qitem[item] = qitem
            # attach to parent or top-level
            if parent_qitem is None:
                self._tree_widget.addTopLevelItem(qitem)
            else:
                parent_qitem.addChild(qitem)

            # recurse on children if available
            try:
                children = getattr(item, "children", None)
                if callable(children):
                    childs = children()
                else:
                    childs = children or []
            except Exception:
                childs = []
            # many YTreeItem implementations may expose _children or similar; try common patterns
            if not childs:
                try:
                    childs = getattr(item, "_children", []) or []
                except Exception:
                    childs = []

            for c in childs:
                _add_recursive(qitem, c)

            return qitem

        for it in list(getattr(self, "_items", []) or []):
            try:
                _add_recursive(None, it)
            except Exception:
                pass

        # expand top-level by default to show items (mirror libyui reasonable behavior)
        try:
            self._tree_widget.expandAll()
        except Exception:
            pass

    def currentItem(self):
        """Return the logical YTreeItem corresponding to the current/focused QTreeWidgetItem."""
        if not self._tree_widget:
            return None
        try:
            qcur = self._tree_widget.currentItem()
            if qcur is None:
                # fallback to first selected item if current not set
                sel = self._tree_widget.selectedItems()
                qcur = sel[0] if sel else None
            if qcur is None:
                return None
            return self._qitem_to_item.get(qcur, None)
        except Exception:
            return None

    def activate(self):
        """Simulate activation of the current item (post Activated event)."""
        item = self.currentItem()
        if item is None:
            return False
        try:
            dlg = self.findDialog()
            if dlg is not None and self.notify():
                dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
            return True
        except Exception:
            return False

    def immediateMode(self):
        return bool(self._immediate)

    def setImmediateMode(self, on=True):
        self._immediate = bool(on)

    # selection change handler
    def _on_selection_changed(self):
        # if immediate mode, post selection-changed event immediately
        try:
            if self._immediate and self.notify():
                dlg = self.findDialog()
                if dlg is not None and self.notify():
                    dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
        except Exception:
            pass

    # item activated (double click / Enter)
    def _on_item_activated(self, qitem, column):
        try:
            # map to logical item
            item = self._qitem_to_item.get(qitem, None)
            if item is None:
                return
            # post activated event
            dlg = self.findDialog()
            if dlg is not None and self.notify():
                dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
        except Exception:
            pass

    def addItem(self, item):
        '''Add a YItem redefinition from YSelectionWidget to manage YTreeItems.'''
        if isinstance(item, str):
            item = YTreeItem(item)            
            self._items.append(item)
        else:
            super().addItem(item)

    # property API hooks (minimal implementation)
    def setProperty(self, propertyName, val):
        try:
            if propertyName == "immediateMode":
                self.setImmediateMode(bool(val))
                return True
        except Exception:
            pass
        return False

    def getProperty(self, propertyName):
        try:
            if propertyName == "immediateMode":
                return self.immediateMode()
        except Exception:
            pass
        return None

    def _set_backend_enabled(self, enabled):
        """Enable/disable the tree widget and propagate to logical items/widgets."""
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass
        # logical propagation to child YWidgets (if any)
        try:
            for c in list(getattr(self, "_items", []) or []):
                try:
                    if hasattr(c, "setEnabled"):
                        c.setEnabled(enabled)
                except Exception:
                    pass
        except Exception:
            pass
