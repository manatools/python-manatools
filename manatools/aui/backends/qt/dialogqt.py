# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains all Qt backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''

from PySide6 import QtWidgets, QtCore, QtGui
from ...yui_common import (
    YSingleChildContainerWidget,
    YUIDimension,
    YPropertySet,
    YProperty,
    YPropertyType,
    YUINoDialogException,
    YDialogType,
    YDialogColorMode,
    YEvent,
    YCancelEvent,
    YTimeoutEvent,
)
from .commonqt import _resolve_icon
from ... import yui as yui_mod
import os
import logging
import signal
import fcntl

class YDialogQt(YSingleChildContainerWidget):
    """Qt6 main window wrapper that manages dialog state and default buttons."""
    _open_dialogs = []
    
    def __init__(self, dialog_type=YDialogType.YMainDialog, color_mode=YDialogColorMode.YDialogNormalColor):
        super().__init__()
        self._dialog_type = dialog_type
        self._color_mode = color_mode
        self._is_open = False
        self._qwidget = None
        self._event_result = None
        self._qt_event_loop = None
        # SIGINT handling state
        self._sigint_r = None
        self._sigint_w = None
        self._sigint_notifier = None
        self._prev_wakeup_fd = None
        self._prev_sigint_handler = None
        self._default_button = None
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
        self._clear_default_button()
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
    def deleteAllDialogs(cls, doThrow=True):
        """Delete all open dialogs (best-effort)."""
        ok = True
        try:
            while cls._open_dialogs:
                try:
                    dlg = cls._open_dialogs[-1]
                    dlg.destroy(doThrow)
                except Exception:
                    ok = False
                    try:
                        cls._open_dialogs.pop()
                    except Exception:
                        break
        except Exception:
            ok = False
        return ok
    
    @classmethod
    def currentDialog(cls, doThrow=True):
        if not cls._open_dialogs:
            if doThrow:
                raise YUINoDialogException("No dialog open")
            return None
        return cls._open_dialogs[-1]

    def setDefaultButton(self, button):
        """Set or clear the default push button for this dialog."""
        if button is None:
            self._clear_default_button()
            return True
        try:
            if button.widgetClass() != "YPushButton":
                raise ValueError("Default button must be a YPushButton")
        except Exception:
            self._logger.error("Invalid widget passed to setDefaultButton", exc_info=True)
            return False
        try:
            dlg = button.findDialog() if hasattr(button, "findDialog") else None
        except Exception:
            dlg = None
        if dlg not in (None, self):
            self._logger.error("Refusing to reuse a button owned by a different dialog")
            return False
        try:
            button.setDefault(True)
        except Exception:
            self._logger.exception("Failed to flag button as default")
            return False
        return True
    
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
                            app_qicon = _resolve_icon(icon_spec)
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
            layout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
            layout.addWidget(self.child().get_backend_widget())
            # If the child is a layout box with a menubar as first child, Qt can display QMenuBar inline.
            # Alternatively, backends may add YMenuBarQt directly to layout.
        
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

        # Robust SIGINT (Ctrl-C) handling: use wakeup fd + QSocketNotifier to exit loop
        self._setup_sigint_notifier(loop)

        # PySide6 / Qt6 uses exec()
        loop.exec()

        # cleanup
        if timer and timer.isActive():
            timer.stop()
        # teardown SIGINT notifier and restore previous wakeup fd
        self._teardown_sigint_notifier()
        self._qt_event_loop = None
        return self._event_result if self._event_result is not None else YEvent()

    def _setup_sigint_notifier(self, loop):
        """Install a wakeup fd and QSocketNotifier to gracefully quit on Ctrl-C."""
        try:
            # create non-blocking pipe
            rfd, wfd = os.pipe()
            for fd in (rfd, wfd):
                try:
                    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                except Exception:
                    pass
            prev = None
            try:
                # store previous wakeup fd to restore later
                prev = signal.set_wakeup_fd(wfd)
            except Exception:
                prev = None
            self._sigint_r = rfd
            self._sigint_w = wfd
            self._prev_wakeup_fd = prev
            # install a noop SIGINT handler to prevent KeyboardInterrupt
            try:
                self._prev_sigint_handler = signal.getsignal(signal.SIGINT)
            except Exception:
                self._prev_sigint_handler = None
            try:
                def _noop_sigint(_sig, _frm):
                    # no-op; wakeup fd + notifier will handle termination
                    pass
                signal.signal(signal.SIGINT, _noop_sigint)
            except Exception:
                pass
            # notifier to watch read end
            notifier = QtCore.QSocketNotifier(self._sigint_r, QtCore.QSocketNotifier.Read)
            def _on_readable():
                try:
                    # drain bytes written by signal module
                    while True:
                        try:
                            os.read(self._sigint_r, 1024)
                        except BlockingIOError:
                            break
                        except KeyboardInterrupt:
                            # suppress default Ctrl-C exception; we'll quit gracefully
                            break
                        except Exception:
                            break
                except Exception:
                    pass
                # Post cancel event and quit the loop
                try:
                    self._post_event(YCancelEvent())
                except Exception:
                    pass
                try:
                    if loop is not None and loop.isRunning():
                        loop.quit()
                except Exception:
                    pass
            notifier.activated.connect(_on_readable)
            self._sigint_notifier = notifier
        except Exception:
            # fall back: plain signal handler attempting to quit
            def _on_sigint(_sig, _frm):
                try:
                    self._post_event(YCancelEvent())
                except Exception:
                    pass
                try:
                    if loop is not None and loop.isRunning():
                        loop.quit()
                except Exception:
                    pass
            try:
                signal.signal(signal.SIGINT, _on_sigint)
            except Exception:
                pass

    def _teardown_sigint_notifier(self):
        """Remove SIGINT notifier and restore previous wakeup fd."""
        try:
            if self._sigint_notifier is not None:
                try:
                    self._sigint_notifier.setEnabled(False)
                except Exception:
                    pass
                self._sigint_notifier = None
        except Exception:
            pass
        try:
            if self._sigint_r is not None:
                try:
                    os.close(self._sigint_r)
                except Exception:
                    pass
                self._sigint_r = None
            if self._sigint_w is not None:
                try:
                    os.close(self._sigint_w)
                except Exception:
                    pass
                self._sigint_w = None
        except Exception:
            pass
        try:
            # restore previous wakeup fd
            if self._prev_wakeup_fd is not None:
                try:
                    signal.set_wakeup_fd(self._prev_wakeup_fd)
                except Exception:
                    pass
            else:
                # reset to default (no wakeup fd)
                try:
                    signal.set_wakeup_fd(-1)
                except Exception:
                    pass
        except Exception:
            pass
        # restore previous SIGINT handler
        try:
            if self._prev_sigint_handler is not None:
                try:
                    signal.signal(signal.SIGINT, self._prev_sigint_handler)
                except Exception:
                    pass
            else:
                try:
                    signal.signal(signal.SIGINT, signal.default_int_handler)
                except Exception:
                    pass
        except Exception:
            pass

    def _register_default_button(self, button):
        """Ensure only one Qt push button is tracked as default."""
        if getattr(self, "_default_button", None) == button:
            return
        if getattr(self, "_default_button", None) is not None:
            try:
                self._default_button._apply_default_state(False, notify_dialog=False)
            except Exception:
                self._logger.exception("Failed to clear previous default button")
        self._default_button = button

    def _unregister_default_button(self, button):
        """Drop reference when the dialog loses its default button."""
        if getattr(self, "_default_button", None) == button:
            self._default_button = None

    def _clear_default_button(self):
        """Clear existing default button, if any."""
        if getattr(self, "_default_button", None) is not None:
            try:
                self._default_button._apply_default_state(False, notify_dialog=False)
            except Exception:
                self._logger.exception("Failed to reset default button state")
            self._default_button = None

