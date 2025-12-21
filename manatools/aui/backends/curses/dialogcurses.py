# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.curses contains all curses backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.curses
'''
import curses
import curses.ascii
import sys
import os
import time
import logging
from ...yui_common import *
from ... import yui as yui_mod

# Module-level safe logging setup for dialog backend; main application may override
_mod_logger = logging.getLogger("manatools.aui.curses.dialog.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)

class YDialogCurses(YSingleChildContainerWidget):
    _open_dialogs = []
    _current_dialog = None
    
    def __init__(self, dialog_type=YDialogType.YMainDialog, color_mode=YDialogColorMode.YDialogNormalColor):
        super().__init__()
        # per-instance logger
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        self._logger.debug("YDialogCurses.__init__ dialog_type=%s color_mode=%s", dialog_type, color_mode)
        self._dialog_type = dialog_type
        self._color_mode = color_mode
        self._is_open = False
        self._window = None
        self._focused_widget = None
        self._last_draw_time = 0
        self._draw_interval = 0.1  # seconds
        self._event_result = None
        # Debounce for resize handling (avoid flicker)
        self._resize_pending_until = 0.0
        self._last_term_size = (0, 0)  # (h, w)
        YDialogCurses._open_dialogs.append(self)
    
    def widgetClass(self):
        return "YDialog"
    
    @staticmethod
    def currentDialog(doThrow=True):
        open_dialog = YDialogCurses._open_dialogs[-1] if YDialogCurses._open_dialogs else None
        if not open_dialog and doThrow:
            raise YUINoDialogException("No dialog is currently open")
        return open_dialog

    @staticmethod
    def topmostDialog(doThrow=True):
        ''' same as currentDialog '''
        return YDialogCurses.currentDialog(doThrow=doThrow)
    
    def isTopmostDialog(self):
        '''Return whether this dialog is the topmost open dialog.'''
        return YDialogCurses._open_dialogs[-1] == self if YDialogCurses._open_dialogs else False

    def open(self):
        if not self._window:
            self._create_backend_widget()
        
        self._is_open = True
        YDialogCurses._current_dialog = self
        self._logger.debug("dialog opened; current_dialog set")
        
        # Find first focusable widget
        focusable = self._find_focusable_widgets()
        if focusable:
            self._focused_widget = focusable[0]
            self._focused_widget._focused = True
        
        # open() must be non-blocking (finalize and show). Event loop is
        # started by waitForEvent() to match libyui semantics.
        return True
    
    def isOpen(self):
        return self._is_open
    
    def destroy(self, doThrow=True):
        self._is_open = False
        if self in YDialogCurses._open_dialogs:
            YDialogCurses._open_dialogs.remove(self)
        if YDialogCurses._current_dialog == self:
            YDialogCurses._current_dialog = None
        try:
            self._logger.debug("dialog destroyed; remaining open=%d", len(YDialogCurses._open_dialogs))
        except Exception:
            pass
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
        # Use the main screen
        self._backend_widget = curses.newwin(0, 0, 0, 0)
        try:
            self._logger.debug("_create_backend_widget created backend window")
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        """Enable/disable the dialog and propagate to contained widgets."""
        try:
            # propagate logical enabled state to entire subtree using setEnabled on children
            # so each widget's hook executes and updates its state.
            child = self.child()
            if child is not None:
                child.setEnabled(enabled)
            
            # If disabling and dialog had focused widget, clear focus
            if not enabled:
                try:
                    if getattr(self, "_focused_widget", None):
                        self._focused_widget._focused = False
                        self._focused_widget = None
                except Exception:
                    pass
            # Force a redraw so disabled/enabled visual state appears immediately
            try:
                self._last_draw_time = 0
            except Exception:
                pass
        except Exception:
            pass

    def _draw_dialog(self):
        """Draw the entire dialog (called by event loop)"""
        if not hasattr(self, '_backend_widget') or not self._backend_widget:
            return
            
        try:
            height, width = self._backend_widget.getmaxyx()
            
            # Clear screen
            self._backend_widget.clear()

            # Draw border
            self._backend_widget.border()
            
            # Draw title
            title = " manatools YUI NCurses Dialog "
            try:                
                appobj = yui_mod.YUI.ui().application()
                atitle = appobj.applicationTitle()
                if atitle:
                    title = atitle
                appobj.setApplicationTitle(title)
            except Exception:
                # ignore and keep default
                pass
            title_x = max(0, (width - len(title)) // 2)
            self._backend_widget.addstr(0, title_x, title, curses.A_BOLD)
            
            # Draw content area - fixed coordinates for child
            content_height = height - 4
            content_width = width - 4
            content_y = 2
            content_x = 2
            
            # Draw child content
            if self.hasChildren():
                self._draw_child_content(content_y, content_x, content_width, content_height)
            
            # Draw footer with instructions
            footer_text = " TAB=Navigate | SPACE=Expand | ENTER=Select | F10/Q=Quit "
            footer_x = max(0, (width - len(footer_text)) // 2)
            if footer_x + len(footer_text) < width:
                self._backend_widget.addstr(height - 1, footer_x, footer_text, curses.A_DIM)
            
            # Draw focus indicator
            if self._focused_widget:
                focus_text = f" Focus: {getattr(self._focused_widget, '_label', 'Unknown')} "
                if len(focus_text) < width:
                    self._backend_widget.addstr(height - 1, 2, focus_text, curses.A_REVERSE)
                #if the focused widget has an expnded list (menus, combos,...), draw it on top
                if hasattr(self._focused_widget, "_draw_expanded_list"):
                    self._focused_widget._draw_expanded_list(self._backend_widget)
            
            # Refresh main window first
            self._backend_widget.refresh()
            
        except curses.error as e:
            # Ignore curses errors (like writing beyond screen bounds)
            pass

    def _draw_child_content(self, start_y, start_x, max_width, max_height):
        """Draw the child widget content respecting container hierarchy"""
        if not self.hasChildren():
            return
            
        # Draw only the root child - it will handle drawing its own children
        child = self.child()
        if hasattr(child, '_draw'):
            child._draw(self._backend_widget, start_y, start_x, max_width, max_height)            
        

    def _cycle_focus(self, forward=True):
        """Cycle focus between focusable widgets"""
        focusable = self._find_focusable_widgets()
        if not focusable:
            return
        
        current_index = -1
        if self._focused_widget:
            for i, widget in enumerate(focusable):
                if widget == self._focused_widget:
                    current_index = i
                    break
        
        if current_index == -1:
            new_index = 0
        else:
            if forward:
                new_index = (current_index + 1) % len(focusable)
            else:
                new_index = (current_index - 1) % len(focusable)
        
        # If the currently focused widget is an expanded combo, collapse it
        # so tabbing away closes the dropdown but does not change selection.
        if self._focused_widget:
            try:
                if getattr(self._focused_widget, "_expanded", False):
                    self._focused_widget._expanded = False
            except Exception:
                pass
            self._focused_widget._focused = False
        
        self._focused_widget = focusable[new_index]
        self._focused_widget._focused = True
        # Force redraw on focus change
        self._last_draw_time = 0

    def _find_focusable_widgets(self):
        """Find all widgets that can receive focus"""
        focusable = []
        
        def find_in_widget(widget):
            if hasattr(widget, '_can_focus') and widget._can_focus:
                focusable.append(widget)
            for child in widget._children:
                find_in_widget(child)
        
        if self.hasChildren():
            find_in_widget(self.child())
        
        return focusable

    
    def _post_event(self, event):
        """Post an event to this dialog; waitForEvent will return it."""
        self._event_result = event
        # If dialog is not open anymore, ensure cleanup
        if isinstance(event, YCancelEvent):
            # Mark closed so loop can clean up
            self._is_open = False

    def waitForEvent(self, timeout_millisec=0):
        """
        Run the ncurses event loop until an event is posted or timeout occurs.
        timeout_millisec == 0 -> block indefinitely until an event (no timeout).
        Returns a YEvent (YWidgetEvent, YTimeoutEvent, YCancelEvent, ...).
        """
        from manatools.aui.yui import YUI
        ui = YUI.ui()

        # Ensure dialog is open/finalized
        if not self._is_open:
            self.open()

        self._event_result = None
        deadline = None
        if timeout_millisec and timeout_millisec > 0:
            deadline = time.time() + (timeout_millisec / 1000.0)

        while self._is_open and self._event_result is None:
            try:
                now = time.time()

                # Apply pending resize once debounce expires
                if self._resize_pending_until and now >= self._resize_pending_until:
                    try:
                        ui._stdscr.clear()
                        ui._stdscr.refresh()
                        new_h, new_w = ui._stdscr.getmaxyx()
                        try:
                            curses.resizeterm(new_h, new_w)
                        except Exception:
                            pass
                        # Recreate backend window (full-screen)
                        self._backend_widget = curses.newwin(new_h, new_w, 0, 0)
                        self._last_term_size = (new_h, new_w)
                    except Exception:
                        pass
                    # Clear pending flag and force immediate redraw
                    self._resize_pending_until = 0.0
                    self._last_draw_time = 0

                # Draw at most every _draw_interval; forced redraw uses last_draw_time = 0
                if (now - self._last_draw_time) >= self._draw_interval:
                    self._draw_dialog()
                    self._last_draw_time = now

                # Non-blocking input
                ui._stdscr.nodelay(True)
                key = ui._stdscr.getch()

                if key == -1:
                    if deadline and time.time() >= deadline:
                        self._event_result = YTimeoutEvent()
                        break
                    time.sleep(0.01)
                    continue

                # Global keys
                if key == curses.KEY_F10 or key == ord('q') or key == ord('Q'):
                    self._post_event(YCancelEvent())
                    break
                elif key == curses.KEY_RESIZE:
                    # Debounce resize; do not redraw immediately to avoid flicker
                    try:
                        new_h, new_w = ui._stdscr.getmaxyx()
                        self._last_term_size = (new_h, new_w)
                    except Exception:
                        pass
                    # Wait 150ms after the last resize event before applying
                    self._resize_pending_until = time.time() + 0.15
                    continue

                # Focus navigation
                if key == ord('\t'):
                    self._cycle_focus(forward=True)
                    self._last_draw_time = 0
                    continue
                elif key == curses.KEY_BTAB:
                    self._cycle_focus(forward=False)
                    self._last_draw_time = 0
                    continue

                # Dispatch key to focused widget
                if self._focused_widget and hasattr(self._focused_widget, '_handle_key'):
                    handled = self._focused_widget._handle_key(key)
                    if handled:
                        self._last_draw_time = 0

            except KeyboardInterrupt:
                self._post_event(YCancelEvent())
                break
            except Exception:
                time.sleep(0.05)

        if self._event_result is None:
            if not self._is_open:
                self._event_result = YCancelEvent()
            elif deadline and time.time() >= deadline:
                self._event_result = YTimeoutEvent()

        if not self._is_open:
            try:
                self.destroy()
            except Exception:
                pass

        return self._event_result if self._event_result is not None else YEvent()
