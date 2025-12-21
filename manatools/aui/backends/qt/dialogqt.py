# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains all Qt backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''

from PySide6 import QtWidgets, QtCore, QtGui
from ...yui_common import YSingleChildContainerWidget, YUIDimension, YPropertySet, YProperty, YPropertyType, YUINoDialogException, YDialogType, YDialogColorMode, YEvent, YCancelEvent, YTimeoutEvent
from ... import yui as yui_mod
import os
import logging

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
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
    
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
        title = "Manatools Qt Dialog"
        
        try:
            appobj = yui_mod.YUI.ui().application()
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
        
        if self.child():
            layout = QtWidgets.QVBoxLayout(central_widget)
            layout.addWidget(self.child().get_backend_widget())
        
        self._backend_widget = self._qwidget
        self._qwidget.closeEvent = self._on_close_event
        self._backend_widget.setEnabled(bool(self._enabled))
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass
    
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
            if self.child():
                try:
                    self.child().setEnabled(enabled)
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
