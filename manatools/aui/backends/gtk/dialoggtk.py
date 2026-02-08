# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.gtk contains all GTK backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
'''

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, GObject, GdkPixbuf, GLib
import cairo
import threading
import os
import logging
from ...yui_common import *
from ... import yui as yui_mod

class YDialogGtk(YSingleChildContainerWidget):
    """Gtk4 dialog window with nested-loop event handling and default button support."""
    _open_dialogs = []
    
    def __init__(self, dialog_type=YDialogType.YMainDialog, color_mode=YDialogColorMode.YDialogNormalColor):
        super().__init__()
        self._dialog_type = dialog_type
        self._color_mode = color_mode
        self._is_open = False
        self._window = None
        self._event_result = None
        self._glib_loop = None
        self._default_button = None
        self._default_key_controller = None
        YDialogGtk._open_dialogs.append(self)
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
    
    def widgetClass(self):
        return "YDialog"
    
    @staticmethod
    def currentDialog(doThrow=True):
        open_dialog = YDialogGtk._open_dialogs[-1] if YDialogGtk._open_dialogs else None
        if not open_dialog and doThrow:
            raise YUINoDialogException("No dialog is currently open")
        return open_dialog

    @staticmethod
    def topmostDialog(doThrow=True):
        ''' same as currentDialog '''
        return YDialogGtk.currentDialog(doThrow=doThrow)
    
    def isTopmostDialog(self):
        '''Return whether this dialog is the topmost open dialog.'''
        return YDialogGtk._open_dialogs[-1] == self if YDialogGtk._open_dialogs else False

    def open(self):
        # Finalize and show the dialog in a non-blocking way.
        if not self._is_open:
            if not self._window:
                self._create_backend_widget()
            # in Gtk4, show_all is not recommended; use present() or show
            try:
                self._window.present()
            except Exception:
                try:
                    self._window.show()
                except Exception:
                    pass
            self._is_open = True
    
    def isOpen(self):
        return self._is_open
    
    def destroy(self, doThrow=True):
        self._clear_default_button()
        if self._window:
            try:
                self._window.destroy()
            except Exception:
                try:
                    self._window.close()
                except Exception:
                    pass
            self._window = None
        self._is_open = False
        if self in YDialogGtk._open_dialogs:
            YDialogGtk._open_dialogs.remove(self)
        
        # Stop GLib main loop if no dialogs left (nested loops only)
        if not YDialogGtk._open_dialogs:
            try:
                if self._glib_loop and self._glib_loop.is_running():
                    self._glib_loop.quit()
            except Exception:
                pass
        return True

    def _post_event(self, event):
        """Internal: post an event to this dialog and quit local GLib.MainLoop if running."""
        self._event_result = event
        if self._glib_loop is not None and self._glib_loop.is_running():
            try:
                self._glib_loop.quit()
            except Exception:
                pass

    def waitForEvent(self, timeout_millisec=0):
        """
        Run a GLib.MainLoop until an event is posted or timeout occurs.
        Returns a YEvent (YWidgetEvent, YTimeoutEvent, ...).
        """
        # Ensure dialog is finalized/open (finalize if caller didn't call open()).
        if not self.isOpen():
            self.open()            

        # Let GTK/GLib process pending events (show/layout) before entering nested loop.
        # Gtk.events_pending()/Gtk.main_iteration() do not exist in GTK4; use MainContext iteration.
        try:
            ctx = GLib.MainContext.default()
            while ctx.pending():
                ctx.iteration(False)
        except Exception:
            # be defensive if API differs on some bindings
            pass

        self._event_result = None
        self._glib_loop = GLib.MainLoop()
 
        def on_timeout():
            # post timeout event and quit loop
            try:
                self._event_result = YTimeoutEvent()
            except Exception:
                pass
            # mark timeout id consumed so cleanup won't try to remove it again
            try:
                self._timeout_id = None
            except Exception:
                pass
            try:
                if self._glib_loop.is_running():
                    self._glib_loop.quit()
            except Exception:
                pass
            return False  # don't repeat

        self._timeout_id = None
        if timeout_millisec and timeout_millisec > 0:
            self._timeout_id = GLib.timeout_add(timeout_millisec, on_timeout)

        # Handle Ctrl-C gracefully: add a GLib SIGINT source to quit the loop and post CancelEvent
        self._sigint_source_id = None
        try:
            def _on_sigint(*_args):
                try:
                    self._post_event(YCancelEvent())
                except Exception:
                    pass
                try:
                    if self._glib_loop.is_running():
                        self._glib_loop.quit()
                except Exception:
                    pass
                return True
            # GLib.unix_signal_add is available on Linux; use default priority
            if hasattr(GLib, 'unix_signal_add'):
                self._sigint_source_id = GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, 2, _on_sigint)  # 2 = SIGINT
        except Exception:
            self._sigint_source_id = None

        # run nested loop; suppress KeyboardInterrupt raised by GI fallback on exit
        try:
            self._glib_loop.run()
        except KeyboardInterrupt:
            # Convert to a cancel event and continue cleanup
            try:
                self._event_result = YCancelEvent()
            except Exception:
                pass

        # cleanup
        if self._timeout_id:
            try:
                GLib.source_remove(self._timeout_id)
            except Exception:
                pass
            self._timeout_id = None
        # remove SIGINT source if installed
        try:
            if self._sigint_source_id:
                GLib.source_remove(self._sigint_source_id)
        except Exception:
            pass
        self._sigint_source_id = None
        self._glib_loop = None
        return self._event_result if self._event_result is not None else YEvent()

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
            self._logger.error("Refusing to set a default button owned by another dialog")
            return False
        try:
            button.setDefault(True)
        except Exception:
            self._logger.exception("Failed to activate default button")
            return False
        return True
    
    def _create_backend_widget(self):
        # Determine window title from YApplicationGtk instance stored on the YUI backend
        title = "Manatools GTK Dialog"
        try:
            appobj = yui_mod.YUI.ui().application()
            atitle = appobj.applicationTitle()
            if atitle:
                title = atitle
            # try to obtain resolved pixbuf from application and store for window icon
            _resolved_pixbuf = None
            try:
                _resolved_pixbuf = getattr(appobj, "_gtk_icon_pixbuf", None)
            except Exception:
                _resolved_pixbuf = None
        except Exception:
            try:
                self._logger.warning("Could not determine application title for dialog", exc_info=True)
            except Exception:
                pass
            pass

        # Create Gtk4 Window
        self._window = Gtk.Window(title=title)
        # set window icon if available
        try:
            if _resolved_pixbuf is not None:
                try:
                    self._window.set_icon(_resolved_pixbuf)
                except Exception:
                    try:
                        # fallback to name if pixbuf not accepted
                        icname = getattr(appobj, "applicationIcon", lambda : None)()
                        if icname:
                            self._window.set_icon_name(icname)
                    except Exception:
                        pass
            else:
                try:
                    # try setting icon name if application provided it
                    icname = getattr(appobj, "applicationIcon", lambda : None)()
                    if icname:
                        self._window.set_icon_name(icname)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self._window.set_default_size(600, 400)
        except Exception:
            pass

        # Content container with margins (window.set_child used in Gtk4)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        content.set_margin_start(10)
        content.set_margin_end(10)
        content.set_margin_top(10)
        content.set_margin_bottom(10)
        
        child = self.child()
        if child:
            child_widget = child.get_backend_widget()
            # ensure child is shown properly
            try:
                content.append(child_widget)
            except Exception:
                try:
                    content.add(child_widget)
                except Exception:
                    pass

        try:
            self._window.set_child(content)
        except Exception:
            # fallback for older bindings
            try:
                self._window.add(content)
            except Exception:
                pass

        self._backend_widget = self._window
        self._backend_widget.set_sensitive(self._enabled)
        # Install key controller to trigger the default button with Enter/Return.
        try:
            controller = Gtk.EventControllerKey()
            controller.connect("key-pressed", self._on_default_key_pressed)
            self._window.add_controller(controller)
            self._default_key_controller = controller
        except Exception:
            self._logger.exception("Failed to install default button key controller")
        # Connect destroy/close handlers
        try:
            # Gtk4: use 'close-request' if available, otherwise 'destroy'
            if hasattr(self._window, "connect"):
                try:
                    self._window.connect("close-request", self._on_delete_event)
                except Exception:
                    try:
                        self._window.connect("destroy", self._on_destroy)
                    except Exception:
                        pass
        except Exception:
            self._logger.error("Failed to connect window close/destroy handlers", exc_info=True)
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass
    
    def _on_destroy(self, widget):
        try:
            self.destroy()
        except Exception:
            pass

    def _on_delete_event(self, *args):
        # close-request handler in Gtk4: post cancel event and destroy
        try:
            self._post_event(YCancelEvent())
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
        # returning False/True not used in this simplified handler
        return False

    def setVisible(self, visible):
        """Set widget visibility."""
        if self._backend_widget:
            try:
                self._backend_widget.set_visible(visible)
            except Exception:
                pass
        super().setVisible(visible)

    def _set_backend_enabled(self, enabled):
        """Enable/disable the dialog window backend."""
        try:
            if self._window is not None:
                try:
                    self._window.set_sensitive(enabled)
                except Exception:
                    # fallback: propagate to child content
                    try:
                        child = getattr(self, "_window", None)
                        if child and hasattr(child, "set_sensitive"):
                            child.set_sensitive(enabled)
                    except Exception:
                        pass
        except Exception:
            pass

    def _on_default_key_pressed(self, controller, keyval, keycode, state):
        """Activate the default button when Return/Enter is pressed."""
        try:
            if keyval in (Gdk.KEY_Return, Gdk.KEY_ISO_Enter, Gdk.KEY_KP_Enter):
                if self._activate_default_button():
                    return True
        except Exception:
            self._logger.exception("Default key handler failed")
        return False

    def _register_default_button(self, button):
        """Ensure this dialog tracks a single default push button."""
        if getattr(self, "_default_button", None) == button:
            return
        if getattr(self, "_default_button", None) is not None:
            try:
                self._default_button._apply_default_state(False, notify_dialog=False)
            except Exception:
                self._logger.exception("Failed to clear previous default button")
        self._default_button = button

    def _unregister_default_button(self, button):
        """Drop dialog reference when button is no longer default."""
        if getattr(self, "_default_button", None) == button:
            self._default_button = None

    def _clear_default_button(self):
        """Clear any current default button."""
        if getattr(self, "_default_button", None) is not None:
            try:
                self._default_button._apply_default_state(False, notify_dialog=False)
            except Exception:
                self._logger.exception("Failed to reset default button state")
            self._default_button = None

    def _activate_default_button(self):
        """Invoke the current default button if enabled and visible."""
        button = getattr(self, "_default_button", None)
        if button is None:
            return False
        try:
            if not button.isEnabled() or not button.visible():
                return False
        except Exception:
            return False
        try:
            self._post_event(YWidgetEvent(button, YEventReason.Activated))
            return True
        except Exception:
            self._logger.exception("Failed to activate default button")
            return False
