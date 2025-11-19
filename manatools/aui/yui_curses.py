"""
NCurses backend implementation for YUI
"""

import curses
import curses.ascii
import sys
import os
import time
from .yui_common import *

class YUICurses:
    def __init__(self):
        self._widget_factory = YWidgetFactoryCurses()
        self._optional_widget_factory = None
        self._application = YApplicationCurses()
        self._stdscr = None
        self._colors_initialized = False
        self._running = False
        
        # Initialize curses
        self._init_curses()
    
    def _init_curses(self):
        try:
            self._stdscr = curses.initscr()
            curses.noecho()
            curses.cbreak()
            curses.curs_set(1)  # Show cursor
            self._stdscr.keypad(True)
            
            # Enable colors if available
            if curses.has_colors():
                curses.start_color()
                curses.use_default_colors()
                self._colors_initialized = True
                # Define some color pairs
                curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
                curses.init_pair(2, curses.COLOR_YELLOW, -1)
                curses.init_pair(3, curses.COLOR_GREEN, -1)
                curses.init_pair(4, curses.COLOR_RED, -1)
        except Exception as e:
            print(f"Error initializing curses: {e}")
            self._cleanup_curses()
            raise
    
    def _cleanup_curses(self):
        try:
            if self._stdscr:
                curses.nocbreak()
                self._stdscr.keypad(False)
                curses.echo()
                curses.curs_set(1)
                curses.endwin()
        except:
            pass
    
    def __del__(self):
        self._cleanup_curses()
    
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

class YApplicationCurses:
    def __init__(self):
        self._application_title = "manatools Curses Application"
        self._product_name = "manatools YUI Curses"
        self._icon_base_path = ""
        self._icon = ""

    def iconBasePath(self):
        return self._icon_base_path
    
    def setIconBasePath(self, new_icon_base_path):
        self._icon_base_path = new_icon_base_path
    
    def setProductName(self, product_name):
        self._product_name = product_name
    
    def productName(self):
        return self._product_name

    def setApplicationIcon(self, Icon):
        """Set the application icon."""
        self._icon = Icon

    def applicationIcon(self):
        """Get the application icon."""
        return self._icon

    def setApplicationTitle(self, title):
        """Set the application title."""
        self._application_title = title
        # Update terminal/window title for xterm-like terminals when stdout is a TTY
        escape_sequences = [
            f"\033]0;{title}\007",   # Standard
            f"\033]1;{title}\007",   # Icon name
            f"\033]2;{title}\007",   # Window title
            f"\033]30;{title}\007",  # Konsole variant 1
            f"\033]31;{title}\007",  # Konsole variant 2
        ]
        try:
            for seq in escape_sequences:
                sys.stdout.write(seq)
            sys.stdout.flush()            
        except Exception:
            pass

    def applicationTitle(self):
        """Get the application title."""
        return self._application_title

    def setApplicationIcon(self, Icon):
        """Set the application title."""
        self._icon = Icon

    def applicationIcon(self):
        """Get the application title."""
        return self.__icon

class YWidgetFactoryCurses:
    def __init__(self):
        pass
    
    def createMainDialog(self, color_mode=YDialogColorMode.YDialogNormalColor):
        return YDialogCurses(YDialogType.YMainDialog, color_mode)

    def createPopupDialog(self, color_mode=YDialogColorMode.YDialogNormalColor):
        return YDialogCurses(YDialogType.YMainDialog, color_mode)
    
    def createVBox(self, parent):
        return YVBoxCurses(parent)
    
    def createHBox(self, parent):
        return YHBoxCurses(parent)
    
    def createLabel(self, parent, text, isHeading=False, isOutputField=False):
        return YLabelCurses(parent, text, isHeading, isOutputField)
    
    def createHeading(self, parent, label):
        return YLabelCurses(parent, label, isHeading=True)
    
    def createInputField(self, parent, label, password_mode=False):
        return YInputFieldCurses(parent, label, password_mode)
    
    def createPushButton(self, parent, label):
        return YPushButtonCurses(parent, label)
    
    def createCheckBox(self, parent, label, is_checked=False):
        return YCheckBoxCurses(parent, label, is_checked)
    
    def createComboBox(self, parent, label, editable=False):
        return YComboBoxCurses(parent, label, editable)
    
    def createSelectionBox(self, parent, label):
        return YSelectionBoxCurses(parent, label)

    # Alignment helpers
    def createLeft(self, parent):
        return YAlignmentCurses(parent, horAlign="Left",  vertAlign=None)

    def createRight(self, parent):
        return YAlignmentCurses(parent, horAlign="Right", vertAlign=None)

    def createTop(self, parent):
        return YAlignmentCurses(parent, horAlign=None,   vertAlign="Top")

    def createBottom(self, parent):
        return YAlignmentCurses(parent, horAlign=None,   vertAlign="Bottom")

    def createHCenter(self, parent):
        return YAlignmentCurses(parent, horAlign="HCenter", vertAlign=None)

    def createVCenter(self, parent):
        return YAlignmentCurses(parent, horAlign=None,      vertAlign="VCenter")

    def createHVCenter(self, parent):
        return YAlignmentCurses(parent, horAlign="HCenter", vertAlign="VCenter")


# Curses Widget Implementations
class YDialogCurses(YSingleChildContainerWidget):
    _open_dialogs = []
    _current_dialog = None
    
    def __init__(self, dialog_type=YDialogType.YMainDialog, color_mode=YDialogColorMode.YDialogNormalColor):
        super().__init__()
        self._dialog_type = dialog_type
        self._color_mode = color_mode
        self._is_open = False
        self._window = None
        self._focused_widget = None
        self._last_draw_time = 0
        self._draw_interval = 0.1  # seconds
        self._event_result = None
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
                if appobj:
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
            if self._child:
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
        if not self._child:
            return
            
        # Draw only the root child - it will handle drawing its own children
        if hasattr(self._child, '_draw'):
            self._child._draw(self._backend_widget, start_y, start_x, max_width, max_height)            
        

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
        
        if self._child:
            find_in_widget(self._child)
        
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

        # Main nested loop: iterate until event posted or timeout
        while self._is_open and self._event_result is None:
            try:
                # Draw only if needed (throttle redraws)
                current_time = time.time()
                if current_time - self._last_draw_time >= self._draw_interval:
                    self._draw_dialog()
                    self._last_draw_time = current_time

                # Non-blocking input
                ui._stdscr.nodelay(True)
                key = ui._stdscr.getch()

                if key == -1:
                    # no input; check timeout
                    if deadline and time.time() >= deadline:
                        self._event_result = YTimeoutEvent()
                        break
                    time.sleep(0.01)
                    continue

                # Handle global keys
                if key == curses.KEY_F10 or key == ord('q') or key == ord('Q'):
                    # Post cancel event
                    self._post_event(YCancelEvent())
                    break
                elif key == curses.KEY_RESIZE:
                    # Handle terminal resize - force redraw
                    self._last_draw_time = 0
                    continue

                # Handle tab navigation
                if key == ord('\t'):
                    self._cycle_focus(forward=True)
                    self._last_draw_time = 0  # Force redraw
                    continue
                elif key == curses.KEY_BTAB:  # Shift+Tab
                    self._cycle_focus(forward=False)
                    self._last_draw_time = 0  # Force redraw
                    continue

                # Send key event to focused widget
                if self._focused_widget and hasattr(self._focused_widget, '_handle_key'):
                    handled = self._focused_widget._handle_key(key)
                    if handled:
                        self._last_draw_time = 0  # Force redraw

            except KeyboardInterrupt:
                # treat as cancel
                self._post_event(YCancelEvent())
                break
            except Exception as e:
                # Don't crash on curses errors
                # keep running unless fatal
                time.sleep(0.1)

        # If dialog was closed without explicit event, produce CancelEvent
        if self._event_result is None:
            if not self._is_open:
                self._event_result = YCancelEvent()
            elif deadline and time.time() >= deadline:
                self._event_result = YTimeoutEvent()

        # cleanup if dialog closed
        if not self._is_open:
            try:
                self.destroy()
            except Exception:
                pass

        return self._event_result if self._event_result is not None else YEvent()

class YVBoxCurses(YWidget):
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
        self._backend_widget = None
    
    def _draw(self, window, y, x, width, height):
        # Calculate total fixed height and number of stretchable children
        fixed_height = 0
        stretchable_count = 0
        child_heights = []
        for child in self._children:
            min_height = getattr(child, '_height', 1)
            if child.stretchable(YUIDimension.YD_VERT):
                stretchable_count += 1
                child_heights.append(None)  # placeholder for stretchable
            else:
                fixed_height += min_height
                child_heights.append(min_height)
        
        # Calculate available height for stretchable children
        spacing = len(self._children) - 1
        available_height = max(0, height - fixed_height - spacing)
        stretch_height = available_height // stretchable_count if stretchable_count else 0

        # Assign heights
        for idx, child in enumerate(self._children):
            if child_heights[idx] is None:
                # Stretchable child
                child_heights[idx] = max(1, stretch_height)

        # Draw children
        current_y = y
        for idx, child in enumerate(self._children):
            if not hasattr(child, '_draw'):
                continue
            ch = child_heights[idx]
            if current_y + ch > y + height:
                break
            child._draw(window, current_y, x, width, ch)
            current_y += ch
            if idx < len(self._children) - 1:
                current_y += 1  # spacing

class YHBoxCurses(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._height = 1  # HBox always takes one line
    
    def widgetClass(self):
        return "YHBox"
    
    def _create_backend_widget(self):
        self._backend_widget = None

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

    def _child_min_width(self, child, max_width):
        # Best-effort minimal width heuristic
        try:
            if hasattr(child, "minWidth"):
                return min(max_width, max(1, int(child.minWidth())))
        except Exception:
            pass
        # Heuristics based on common attributes
        try:
            cls = child.widgetClass() if hasattr(child, "widgetClass") else ""
            if cls in ("YLabel", "YPushButton", "YCheckBox"):
                text = getattr(child, "_text", None)
                if text is None:
                    text = getattr(child, "_label", "")
                pad = 4 if cls == "YPushButton" else 0
                return min(max_width, max(1, len(str(text)) + pad))
        except Exception:
            pass
        return max(1, min(10, max_width))  # safe default

    def _draw(self, window, y, x, width, height):
        num_children = len(self._children)
        if num_children == 0 or width <= 0 or height <= 0:
            return

        spacing = max(0, num_children - 1)
        available = max(0, width - spacing)

        # Allocate fixed width for non-stretchable children
        widths = [0] * num_children
        stretchables = []
        fixed_total = 0
        for i, child in enumerate(self._children):
            if child.stretchable(YUIDimension.YD_HORIZ):
                stretchables.append(i)
            else:
                w = self._child_min_width(child, available)
                widths[i] = w
                fixed_total += w

        # Remaining width goes to stretchable children
        remaining = max(0, available - fixed_total)
        if stretchables:
            per = remaining // len(stretchables)
            extra = remaining % len(stretchables)
            for k, idx in enumerate(stretchables):
                widths[idx] = max(1, per + (1 if k < extra else 0))
        else:
            # No stretchables: distribute leftover evenly
            if fixed_total < available:
                leftover = available - fixed_total
                per = leftover // num_children
                extra = leftover % num_children
                for i in range(num_children):
                    base = widths[i] if widths[i] else 1
                    widths[i] = base + per + (1 if i < extra else 0)
            else:
                # If even fixed widths overflow, clamp proportionally
                pass  # widths already reflect minimal values

        # Draw children
        cx = x
        for i, child in enumerate(self._children):
            w = widths[i]
            if w <= 0:
                continue
            if hasattr(child, "_draw"):
                ch = min(height, getattr(child, "_height", height))
                child._draw(window, y, cx, w, ch)
            cx += w
            if i < num_children - 1:
                cx += 1  # one-column spacing

class YLabelCurses(YWidget):
    def __init__(self, parent=None, text="", isHeading=False, isOutputField=False):
        super().__init__(parent)
        self._text = text
        self._is_heading = isHeading
        self._is_output_field = isOutputField
        self._height = 1
        self._focused = False
        self._can_focus = False  # Labels don't get focus
    
    def widgetClass(self):
        return "YLabel"
    
    def text(self):
        return self._text
    
    def setText(self, new_text):
        self._text = new_text
    
    def _create_backend_widget(self):
        self._backend_widget = None
    
    def _draw(self, window, y, x, width, height):
        try:
            attr = 0
            if self._is_heading:
                attr = curses.A_BOLD
            
            # Truncate text to fit available width
            display_text = self._text[:width-1]
            window.addstr(y, x, display_text, attr)
        except curses.error:
            pass

class YInputFieldCurses(YWidget):
    def __init__(self, parent=None, label="", password_mode=False):
        super().__init__(parent)
        self._label = label
        self._value = ""
        self._password_mode = password_mode
        self._cursor_pos = 0
        self._focused = False
        self._can_focus = True
        self._height = 1
    
    def widgetClass(self):
        return "YInputField"
    
    def value(self):
        return self._value
    
    def setValue(self, text):
        self._value = text
        self._cursor_pos = len(text)
    
    def label(self):
        return self._label
    
    def _create_backend_widget(self):
        self._backend_widget = None
    
    def _draw(self, window, y, x, width, height):
        try:
            # Draw label
            if self._label:
                label_text = self._label
                if len(label_text) > width // 3:
                    label_text = label_text[:width // 3]
                window.addstr(y, x, label_text)
                x += len(label_text) + 1
                width -= len(label_text) + 1
            
            # Calculate available space for input
            if width <= 0:
                return
            
            # Prepare display value
            if self._password_mode and self._value:
                display_value = '*' * len(self._value)
            else:
                display_value = self._value
            
            # Handle scrolling for long values
            if len(display_value) > width:
                if self._cursor_pos >= width:
                    start_pos = self._cursor_pos - width + 1
                    display_value = display_value[start_pos:start_pos + width]
                else:
                    display_value = display_value[:width]
            
            # Draw input field background
            field_bg = ' ' * width
            attr = curses.A_REVERSE if self._focused else curses.A_NORMAL
            window.addstr(y, x, field_bg, attr)
            
            # Draw text
            if display_value:
                window.addstr(y, x, display_value, attr)
            
            # Show cursor if focused
            if self._focused:
                cursor_display_pos = min(self._cursor_pos, width - 1)
                if cursor_display_pos < len(display_value):
                    window.chgat(y, x + cursor_display_pos, 1, curses.A_REVERSE | curses.A_BOLD)
                    
        except curses.error:
            pass
    
    def _handle_key(self, key):
        if not self._focused:
            return False
            
        handled = True
        
        if key == curses.KEY_BACKSPACE or key == 127 or key == 8:
            if self._cursor_pos > 0:
                self._value = self._value[:self._cursor_pos-1] + self._value[self._cursor_pos:]
                self._cursor_pos -= 1
        elif key == curses.KEY_DC:  # Delete key
            if self._cursor_pos < len(self._value):
                self._value = self._value[:self._cursor_pos] + self._value[self._cursor_pos+1:]
        elif key == curses.KEY_LEFT:
            if self._cursor_pos > 0:
                self._cursor_pos -= 1
        elif key == curses.KEY_RIGHT:
            if self._cursor_pos < len(self._value):
                self._cursor_pos += 1
        elif key == curses.KEY_HOME:
            self._cursor_pos = 0
        elif key == curses.KEY_END:
            self._cursor_pos = len(self._value)
        elif 32 <= key <= 126:  # Printable characters
            self._value = self._value[:self._cursor_pos] + chr(key) + self._value[self._cursor_pos:]
            self._cursor_pos += 1
        else:
            handled = False
        
        return handled

class YPushButtonCurses(YWidget):
    def __init__(self, parent=None, label=""):
        super().__init__(parent)
        self._label = label
        self._focused = False
        self._can_focus = True
        self._height = 1  # Fixed height - buttons are always one line
    
    def widgetClass(self):
        return "YPushButton"
    
    def label(self):
        return self._label
    
    def setLabel(self, label):
        self._label = label
    
    def _create_backend_widget(self):
        self._backend_widget = None
    
    def _draw(self, window, y, x, width, height):
        try:
            # Center the button label within available width
            button_text = f" {self._label} "
            text_x = x + max(0, (width - len(button_text)) // 2)
            
            # Only draw if we have enough space
            if text_x + len(button_text) <= x + width:
                attr = curses.A_REVERSE if self._focused else curses.A_NORMAL
                if self._focused:
                    attr |= curses.A_BOLD
                
                window.addstr(y, text_x, button_text, attr)
        except curses.error:
            # Ignore drawing errors (out of bounds)
            pass
    
    def _handle_key(self, key):
        if not self._focused:
            return False
            
        if key == ord('\n') or key == ord(' '):
            # Button pressed -> post widget event to containing dialog
            dlg = self.findDialog()
            if dlg is not None:
                try:
                    dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
                except Exception:
                    pass
            return True        
        return False

class YCheckBoxCurses(YWidget):
    def __init__(self, parent=None, label="", is_checked=False):
        super().__init__(parent)
        self._label = label
        self._is_checked = is_checked
        self._focused = False
        self._can_focus = True
        self._height = 1
    
    def widgetClass(self):
        return "YCheckBox"
    
    def value(self):
        return self._is_checked
    
    def setValue(self, checked):
        self._is_checked = checked
    
    def label(self):
        return self._label
    
    def _create_backend_widget(self):
        # In curses, there's no actual backend widget, just internal state
        pass
    
    def _draw(self, window, y, x, width, height):
        """Draw the checkbox with its label"""
        try:
            # Draw checkbox symbol: [X] or [ ]
            checkbox_symbol = "[X]" if self._is_checked else "[ ]"
            text = f"{checkbox_symbol} {self._label}"
            
            # Truncate if too wide
            if len(text) > width:
                text = text[:width-3] + "..."
            
            # Draw with highlighting if focused
            if self._focused:
                window.attron(curses.A_REVERSE)
            
            window.addstr(y, x, text)
            
            if self._focused:
                window.attroff(curses.A_REVERSE)
        except curses.error:
            pass
    
    def _handle_key(self, key):
        """Handle keyboard input for checkbox (Space to toggle)"""
        # Space or Enter to toggle
        if key in (ord(' '), ord('\n'), curses.KEY_ENTER):
            self._toggle()
            return True
        return False
    
    def _toggle(self):
        """Toggle checkbox state and post event"""
        self._is_checked = not self._is_checked
        
        if self.notify():
            # Post a YWidgetEvent to the containing dialog
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
            else:
                print(f"CheckBox toggled (no dialog found): {self._label} = {self._is_checked}")

class YComboBoxCurses(YSelectionWidget):
    def __init__(self, parent=None, label="", editable=False):
        super().__init__(parent)
        self._label = label
        self._editable = editable
        self._value = ""
        self._focused = False
        self._can_focus = True
        self._height = 1
        self._expanded = False
        self._hover_index = 0
        self._combo_x = 0
        self._combo_y = 0
        self._combo_width = 0
    
    def widgetClass(self):
        return "YComboBox"
    
    def value(self):
        return self._value
    
    def setValue(self, text):
        self._value = text
        # Update selected items
        self._selected_items = []
        for item in self._items:
            if item.label() == text:
                self._selected_items.append(item)
                break
    
    def editable(self):
        return self._editable
    
    def _create_backend_widget(self):
        self._backend_widget = None
    
    def _draw(self, window, y, x, width, height):
        # Store position and dimensions for dropdown drawing
        self._combo_y = y
        self._combo_x = x
        self._combo_width = width
        
        try:
            # Calculate available space for combo box
            label_space = len(self._label) + 1 if self._label else 0
            combo_space = width - label_space
            
            if combo_space <= 3:  # Need at least space for " ▼ "
                return
            
            # Draw label
            if self._label:
                label_text = self._label
                if len(label_text) > label_space - 1:
                    label_text = label_text[:label_space - 1]
                window.addstr(y, x, label_text)
                x += len(label_text) + 1
            
            # Prepare display value - always show current value
            display_value = self._value if self._value else "Select..."
            max_display_width = combo_space - 3  # Reserve space for " ▼ "
            if len(display_value) > max_display_width:
                display_value = display_value[:max_display_width] + "..."
            
            # Draw combo box background
            combo_bg = " " * combo_space
            attr = curses.A_REVERSE if self._focused else curses.A_NORMAL
            window.addstr(y, x, combo_bg, attr)
            
            # Draw combo box content
            combo_text = f" {display_value} ▼"
            if len(combo_text) > combo_space:
                combo_text = combo_text[:combo_space]
            
            window.addstr(y, x, combo_text, attr)
            
            # Draw expanded list if active
            if self._expanded:
                self._draw_expanded_list(window)
            
        except curses.error:
            # Ignore drawing errors
            pass

    def _draw_expanded_list(self, window):
        """Draw the expanded dropdown list at correct position"""
        if not self._expanded or not self._items:
            return
            
        try:
            # Make sure we don't draw outside screen
            screen_height, screen_width = window.getmaxyx()

            list_height = min(len(self._items), screen_height)
           
            # Calculate dropdown position - right below the combo box
            dropdown_y = self._combo_y + 1
            dropdown_x = self._combo_x + (len(self._label) + 1 if self._label else 0)
            dropdown_width = self._combo_width - (len(self._label) + 1 if self._label else 0)
           
            # If not enough space below, draw above
            if dropdown_y + list_height >= screen_height:
                dropdown_y = max(1, self._combo_y - list_height - 1)
            
            # Ensure dropdown doesn't go beyond right edge
            if dropdown_x + dropdown_width >= screen_width:
                dropdown_width = screen_width - dropdown_x - 1
            
            if dropdown_width <= 5:  # Need reasonable width
                return
            
            # Draw dropdown background for each item
            for i in range(list_height):
                if i >= len(self._items):
                    break
                    
                item = self._items[i]
                item_text = item.label()
                if len(item_text) > dropdown_width - 2:
                    item_text = item_text[:dropdown_width - 2] + "..."
                
                # Highlight hovered item
                attr = curses.A_REVERSE if i == self._hover_index else curses.A_NORMAL
                
                # Create background for the item
                bg_text = " " + item_text.ljust(dropdown_width - 2)
                if len(bg_text) > dropdown_width:
                    bg_text = bg_text[:dropdown_width]
                
                # Ensure we don't write beyond screen bounds
                if (dropdown_y + i < screen_height and 
                    dropdown_x < screen_width and 
                    dropdown_x + len(bg_text) <= screen_width):
                    try:
                        window.addstr(dropdown_y + i, dropdown_x, bg_text, attr)
                    except curses.error:
                        pass  # Ignore out-of-bounds errors
                
        except curses.error:
            # Ignore drawing errors
            pass

    def _handle_key(self, key):
        if not self._focused:
            return False
            
        handled = True
        
        # If currently expanded, give expanded-list handling priority so Enter
        # selects the hovered item instead of simply toggling expansion.
        if self._expanded:
            # Handle navigation in expanded list
            if key == curses.KEY_UP:
                if self._hover_index > 0:
                    self._hover_index -= 1
            elif key == curses.KEY_DOWN:
                if self._hover_index < len(self._items) - 1:
                    self._hover_index += 1
            elif key == ord('\n') or key == ord(' '):
                # Select hovered item
                if self._items and 0 <= self._hover_index < len(self._items):
                    selected_item = self._items[self._hover_index]
                    self.setValue(selected_item.label())  # update internal value/selection
                    self._expanded = False
                    if self.notify():
                        # force parent dialog redraw if present
                        dlg = self.findDialog()
                        if dlg is not None:
                            try:
                                # notify dialog to redraw immediately
                                dlg._last_draw_time = 0
                                # post a widget event for selection change
                                dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
                            except Exception:
                                pass
                    # selection made -> handled
            elif key == 27:  # ESC key
                self._expanded = False
            else:
                handled = False
        else:
            # Not expanded: Enter/Space expands the list
            if key == ord('\n') or key == ord(' '):
                self._expanded = not self._expanded
                if self._expanded and self._items:
                    # Set hover index to current value if exists
                    self._hover_index = 0
                    if self._value:
                        for i, item in enumerate(self._items):
                            if item.label() == self._value:
                                self._hover_index = i
                                break
            else:
                handled = False
        
        return handled

class YSelectionBoxCurses(YSelectionWidget):
    def __init__(self, parent=None, label=""):
        super().__init__(parent)
        self._label = label
        self._value = ""
        self._selected_items = []
        self._multi_selection = False

        # UI state for drawing/navigation
        # actual minimal height for layout (keep small so parent can expand it)
        self._height = 1
        # preferred rows used for paging when no draw happened yet
        self._preferred_rows = 6

        self._scroll_offset = 0
        self._hover_index = 0  # index into self._items (global)
        self._can_focus = True
        self._focused = False
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)

        # Track last computed visible rows during last _draw call so
        # navigation/ensure logic uses actual available space.
        self._current_visible_rows = None

    def widgetClass(self):
        return "YSelectionBox"

    def label(self):
        return self._label

    def value(self):
        return self._value

    def setValue(self, text):
        """Select first item matching text."""
        self._value = text
        # update selected_items
        self._selected_items = [it for it in self._items if it.label() == text][:1]
        # update hover to first matching index
        for idx, it in enumerate(self._items):
            if it.label() == text:
                self._hover_index = idx
                # adjust scroll offset to make hovered visible
                self._ensure_hover_visible()
                break

    def selectedItems(self):
        return list(self._selected_items)

    def selectItem(self, item, selected=True):
        """Programmatically select/deselect an item."""
        # find index
        idx = None
        for i, it in enumerate(self._items):
            if it is item or it.label() == item.label():
                idx = i
                break
        if idx is None:
            return

        if selected:
            if not self._multi_selection:
                self._selected_items = [self._items[idx]]
                self._value = self._items[idx].label()
            else:
                if self._items[idx] not in self._selected_items:
                    self._selected_items.append(self._items[idx])
        else:
            if self._items[idx] in self._selected_items:
                self._selected_items.remove(self._items[idx])
                self._value = self._selected_items[0].label() if self._selected_items else ""

        # ensure hover and scroll reflect this item
        self._hover_index = idx
        self._ensure_hover_visible()

        if self.notify():
            # notify dialog
            try:
                if getattr(self, "notify", lambda: True)():
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
            except Exception:
                pass

    def setMultiSelection(self, enabled):
        self._multi_selection = bool(enabled)
        # if disabling multi-selection, reduce to first selected item
        if not self._multi_selection and len(self._selected_items) > 1:
            first = self._selected_items[0]
            self._selected_items = [first]
            self._value = first.label()

    def multiSelection(self):
        return bool(self._multi_selection)

    def _ensure_hover_visible(self):
        """Adjust scroll offset so that hover_index is visible in the box."""
        # Prefer the visible row count computed during the last _draw call
        # (which takes the actual available height into account). Fallback
        # to the configured visible row count if no draw happened yet.
        visible = self._current_visible_rows if self._current_visible_rows is not None else self._visible_row_count()
        if visible <= 0:
            return
        if self._hover_index < self._scroll_offset:
            self._scroll_offset = self._hover_index
        elif self._hover_index >= self._scroll_offset + visible:
            self._scroll_offset = self._hover_index - visible + 1

    def _visible_row_count(self):
        # Return preferred visible rows for navigation (PageUp/PageDown step).
        # Use preferred_rows (default 6) rather than forcing the layout minimum.
        return max(1, getattr(self, "_preferred_rows", 6))

    def _create_backend_widget(self):
        # No curses backend widget object; drawing handled in _draw.
        # Keep minimal layout height small so parent can give more space.
        self._height = len(self._items) + (1 if self._label else 0)
        # reset scroll/hover if out of range
        if self._hover_index >= len(self._items):
             self._hover_index = max(0, len(self._items) - 1)
        self._ensure_hover_visible()
        # reset the cached visible rows so future navigation uses the next draw's value
        self._current_visible_rows = None

    def _draw(self, window, y, x, width, height):
        """Draw label (optional) and visible portion of items."""
        try:
            line = y
            # draw label if present
            if self._label:
                lbl = self._label
                try:
                    window.addstr(line, x, lbl[:width], curses.A_BOLD)
                except curses.error:
                    pass
                line += 1

            visible = self._visible_row_count()
            # compute how many rows we can actually draw given provided height.
            available_rows = max(0, height - (1 if self._label else 0))
            if self.stretchable(YUIDimension.YD_VERT):
                # If widget is stretchable vertically, use all available rows (up to number of items)
                visible = min(len(self._items), available_rows)
            else:
                # Otherwise prefer configured height but don't exceed available rows or items
                visible = min(len(self._items), self._visible_row_count(), available_rows)
            # remember actual visible rows for navigation logic (_ensure_hover_visible)
            self._current_visible_rows = visible
            for i in range(visible):
                item_idx = self._scroll_offset + i
                if item_idx >= len(self._items):
                    break
                item = self._items[item_idx]
                text = item.label()
                checkbox = "*" if item in self._selected_items else " "
                # Display selection marker for multi or single similarly
                display = f"[{checkbox}] {text}"
                # truncate
                if len(display) > width:
                    display = display[:max(0, width - 3)] + "..."
                attr = curses.A_NORMAL
                if self._focused and item_idx == self._hover_index:
                    attr |= curses.A_REVERSE
                try:
                    window.addstr(line + i, x, display.ljust(width), attr)
                except curses.error:
                    pass

            # if focused and there are more items than visible, show scrollbar hint
            if self._focused and len(self._items) > visible and width > 0:
                try:
                    # show simple up/down markers at rightmost column
                    if self._scroll_offset > 0:
                        window.addch(y + (1 if self._label else 0), x + width - 1, '^')
                    if (self._scroll_offset + visible) < len(self._items):
                        window.addch(y + (1 if self._label else 0) + visible - 1, x + width - 1, 'v')
                except curses.error:
                    pass
            # keep _current_visible_rows until next draw; navigation will use it
        except curses.error:
            pass

    def _handle_key(self, key):
        """Handle navigation and selection keys when focused."""
        if not self._focused:
            return False

        handled = True
        if key == curses.KEY_UP:
            if self._hover_index > 0:
                self._hover_index -= 1
                self._ensure_hover_visible()
        elif key == curses.KEY_DOWN:
            if self._hover_index < max(0, len(self._items) - 1):
                self._hover_index += 1
                self._ensure_hover_visible()
        elif key == curses.KEY_PPAGE:  # PageUp
            step = self._visible_row_count() or 1
            self._hover_index = max(0, self._hover_index - step)
            self._ensure_hover_visible()
        elif key == curses.KEY_NPAGE:  # PageDown
            step = self._visible_row_count() or 1
            self._hover_index = min(max(0, len(self._items) - 1), self._hover_index + step)
            self._ensure_hover_visible()
        elif key == curses.KEY_HOME:
            self._hover_index = 0
            self._ensure_hover_visible()
        elif key == curses.KEY_END:
            self._hover_index = max(0, len(self._items) - 1)
            self._ensure_hover_visible()
        elif key in (ord(' '), ord('\n')):  # toggle/select
            if 0 <= self._hover_index < len(self._items):
                item = self._items[self._hover_index]
                if self._multi_selection:
                    # toggle membership
                    if item in self._selected_items:
                        self._selected_items.remove(item)
                    else:
                        self._selected_items.append(item)
                    # update primary value to first selected or empty
                    self._value = self._selected_items[0].label() if self._selected_items else ""
                else:
                    # single selection: set as sole selected
                    self._selected_items = [item]
                    self._value = item.label()
                # notify dialog of selection change
                try:
                    if getattr(self, "notify", lambda: True)():
                        dlg = self.findDialog()
                        if dlg is not None:
                            dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
                except Exception:
                    pass
        else:
            handled = False

        return handled

class YAlignmentCurses(YSingleChildContainerWidget):
    """
    Single-child alignment container for ncurses. It becomes stretchable on the
    requested axes, and positions the child inside its draw area accordingly.
    """
    def __init__(self, parent=None, horAlign=None, vertAlign=None):
        super().__init__(parent)
        self._halign_spec = horAlign
        self._valign_spec = vertAlign
        self._backend_widget = None  # not used by curses
        self._height = 1

    def widgetClass(self):
        return "YAlignment"

    def stretchable(self, dim):
        if dim == YUIDimension.YD_HORIZ:
            return str(self._halign_spec).lower() in ("right", "hcenter", "hvcenter")
        if dim == YUIDimension.YD_VERT:
            return str(self._valign_spec).lower() in ("vcenter", "hvcenter")
        return False

    def setAlignment(self, horAlign=None, vertAlign=None):
        self._halign_spec = horAlign
        self._valign_spec = vertAlign

    def addChild(self, child):
        try:
            super().addChild(child)
        except Exception:
            self._child = child

    def setChild(self, child):
        try:
            super().setChild(child)
        except Exception:
            self._child = child

    def _create_backend_widget(self):
        self._backend_widget = None
        self._height = max(1, getattr(self._child, "_height", 1) if self._child else 1)

    def _child_min_width(self, child, max_width):
        # Heuristic minimal width similar to YHBoxCurses
        try:
            cls = child.widgetClass() if hasattr(child, "widgetClass") else ""
            if cls in ("YLabel", "YPushButton", "YCheckBox"):
                text = getattr(child, "_text", None)
                if text is None:
                    text = getattr(child, "_label", "")
                pad = 4 if cls == "YPushButton" else 0
                return min(max_width, max(1, len(str(text)) + pad))
        except Exception:
            pass
        return max(1, min(10, max_width))

    def _draw(self, window, y, x, width, height):
        if not self._child or not hasattr(self._child, "_draw"):
            return
        try:
            # width to give to the child: minimal needed (so it can be pushed)
            ch_min_w = self._child_min_width(self._child, width)
            # Horizontal position
            hs = str(self._halign_spec).lower() if self._halign_spec else "left"
            if hs in ("right",):
                cx = x + max(0, width - ch_min_w)
            elif hs in ("hcenter", "center", "centre", "hvcenter"):
                cx = x + max(0, (width - ch_min_w) // 2)
            else:
                cx = x
            # Vertical position (single line widgets mostly)
            vs = str(self._valign_spec).lower() if self._valign_spec else "top"
            if vs in ("vcenter", "center", "centre", "hvcenter"):
                cy = y + max(0, (height - 1) // 2)
            elif vs in ("bottom", "end"):
                cy = y + max(0, height - 1)
            else:
                cy = y
            self._child._draw(window, cy, cx, min(ch_min_w, max(1, width)), min(height, getattr(self._child, "_height", 1)))
        except Exception:
            pass
