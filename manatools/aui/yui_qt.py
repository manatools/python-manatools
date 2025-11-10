"""
Qt backend implementation for YUI
"""

import sys
from PyQt5 import QtWidgets, QtCore, QtGui
from .yui_common import *

class YUIQt:
    def __init__(self):
        self._widget_factory = YWidgetFactoryQt()
        self._optional_widget_factory = None
        self._application = YApplicationQt()
        
        # Ensure QApplication exists
        self._qapp = QtWidgets.QApplication.instance()
        if not self._qapp:
            self._qapp = QtWidgets.QApplication(sys.argv)
    
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

    def applicationTitle(self):
        """Get the application title."""
        return self._application_title

    def setApplicationIcon(self, Icon):
        """Set the application title."""
        self._icon = Icon

    def applicationIcon(self):
        """Get the application title."""
        return self.__icon

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
        self._qwidget.setWindowTitle("YUI Qt Dialog")
        self._qwidget.resize(600, 400)
        
        central_widget = QtWidgets.QWidget()
        self._qwidget.setCentralWidget(central_widget)
        
        if self._child:
            layout = QtWidgets.QVBoxLayout(central_widget)
            layout.addWidget(self._child.get_backend_widget())
        
        self._backend_widget = self._qwidget
        self._qwidget.closeEvent = self._on_close_event
    
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

        loop.exec_()

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
    
    def _create_backend_widget(self):
        self._backend_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self._backend_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        for child in self._children:
            widget = child.get_backend_widget()
            expand = 1 if child.stretchable(YUIDimension.YD_VERT) else 0
            layout.addWidget(widget, stretch=expand)

class YHBoxQt(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def widgetClass(self):
        return "YHBox"
    
    def _create_backend_widget(self):
        self._backend_widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(self._backend_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        for child in self._children:
            widget = child.get_backend_widget()
            expand = 1 if child.stretchable(YUIDimension.YD_HORIZ) else 0
            layout.addWidget(widget, stretch=expand)

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
        self._backend_widget.clicked.connect(self._on_clicked)
    
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
            self._backend_widget.setChecked(checked)
    
    def label(self):
        return self._label
    
    def _create_backend_widget(self):
        self._backend_widget = QtWidgets.QCheckBox(self._label)
        self._backend_widget.setChecked(self._is_checked)
        self._backend_widget.stateChanged.connect(self._on_state_changed)
    
    def _on_state_changed(self, state):
        # Update internal state
        # state is QtCore.Qt.CheckState (Unchecked=0, PartiallyChecked=1, Checked=2)
        self._is_checked = (state == QtCore.Qt.Checked)
        
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
    
    def _on_text_changed(self, text):
        self._value = text
        # Update selected items
        self._selected_items = []
        for item in self._items:
            if item.label() == text:
                self._selected_items.append(item)
                break
        # Post selection-changed event to containing dialog
        try:
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
        except Exception:
            pass