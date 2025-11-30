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
        return YAlignmentCurses(parent, horAlign=YAlignmentType.YAlignBegin,  vertAlign=YAlignmentType.YAlignUnchanged)

    def createRight(self, parent):
        return YAlignmentCurses(parent, horAlign=YAlignmentType.YAlignEnd, vertAlign=YAlignmentType.YAlignUnchanged)

    def createTop(self, parent):
        return YAlignmentCurses(parent, horAlign=YAlignmentType.YAlignUnchanged,   vertAlign=YAlignmentType.YAlignBegin)

    def createBottom(self, parent):
        return YAlignmentCurses(parent, horAlign=YAlignmentType.YAlignUnchanged,   vertAlign=YAlignmentType.YAlignEnd)

    def createHCenter(self, parent):
        return YAlignmentCurses(parent, horAlign=YAlignmentType.YAlignCenter, vertAlign=YAlignmentType.YAlignUnchanged)

    def createVCenter(self, parent):
        return YAlignmentCurses(parent, horAlign=YAlignmentType.YAlignUnchanged,      vertAlign=YAlignmentType.YAlignCenter)

    def createHVCenter(self, parent):
        return YAlignmentCurses(parent, horAlign=YAlignmentType.YAlignCenter, vertAlign=YAlignmentType.YAlignCenter)

    def createAlignment(self, parent, horAlignment: YAlignmentType, vertAlignment: YAlignmentType):
        """Create a generic YAlignment using YAlignmentType enums (or compatible specs)."""
        return YAlignmentCurses(parent, horAlign=horAlignment, vertAlign=vertAlignment)

    def createTree(self, parent, label, multiselection=False, recursiveselection = False):
        """Create a Tree widget."""
        return YTreeCurses(parent, label, multiselection, recursiveselection)    

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

    def _set_backend_enabled(self, enabled):
        """Enable/disable the dialog and propagate to contained widgets."""
        try:
            # propagate logical enabled state to entire subtree using setEnabled on children
            # so each widget's hook executes and updates its state.
            if getattr(self, "_child", None):
                try:
                    self._child.setEnabled(enabled)
                except Exception:
                    pass
            for c in list(getattr(self, "_children", []) or []):
                try:
                    c.setEnabled(enabled)
                except Exception:
                    pass
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

    def _set_backend_enabled(self, enabled):
        """Enable/disable VBox and propagate to logical children."""
        try:
            for c in list(getattr(self, "_children", []) or []):
                try:
                    c.setEnabled(enabled)
                except Exception:
                    pass
        except Exception:
            pass

    def _draw(self, window, y, x, width, height):
        # Vertical layout with spacing; give stretchable children more than their minimum
        num_children = len(self._children)
        if num_children == 0 or height <= 0 or width <= 0:
            return

        spacing = max(0, num_children - 1)

        child_min_heights = []
        stretchable_indices = []
        stretchable_weights = []
        fixed_height_total = 0

        for i, child in enumerate(self._children):
            # child._height is the preferred minimum (may include its own label rows)
            child_min = max(1, getattr(child, "_height", 1))
            child_min_heights.append(child_min)

            is_stretch = bool(child.stretchable(YUIDimension.YD_VERT))
            if is_stretch:
                stretchable_indices.append(i)
                # default vertical weight = 1
                try:
                    w = child.weight(YUIDimension.YD_VERT)
                    w = int(w) if w is not None else 1
                except Exception:
                    w = 1
                if w <= 0:
                    w = 1
                stretchable_weights.append(w)
            else:
                fixed_height_total += child_min

        available_for_stretch = max(0, height - fixed_height_total - spacing)

        allocated = list(child_min_heights)

        if stretchable_indices:
            total_weight = sum(stretchable_weights) or len(stretchable_indices)
            # Proportional distribution of extra rows
            extras = [0] * len(stretchable_indices)
            base = 0
            for k, idx in enumerate(stretchable_indices):
                extra = (available_for_stretch * stretchable_weights[k]) // total_weight
                extras[k] = extra
                base += extra
            # Distribute leftover rows due to integer division
            leftover = available_for_stretch - base
            for k in range(len(stretchable_indices)):
                if leftover <= 0:
                    break
                extras[k] += 1
                leftover -= 1
            for k, idx in enumerate(stretchable_indices):
                allocated[idx] = child_min_heights[idx] + extras[k]

        total_alloc = sum(allocated) + spacing
        if total_alloc < height:
            # Give remainder to the last stretchable (or last child)
            extra = height - total_alloc
            target = stretchable_indices[-1] if stretchable_indices else (num_children - 1)
            allocated[target] += extra
        elif total_alloc > height:
            # Reduce overflow from the last stretchable (or last child)
            diff = total_alloc - height
            target = stretchable_indices[-1] if stretchable_indices else (num_children - 1)
            allocated[target] = max(1, allocated[target] - diff)

        # Draw children with allocated heights
        cy = y
        for i, child in enumerate(self._children):
            ch = allocated[i]
            if ch <= 0:
                continue
            if cy + ch > y + height:
                ch = max(0, (y + height) - cy)
            if ch <= 0:
                break
            try:
                if hasattr(child, "_draw"):
                    child._draw(window, cy, x, width, ch)
            except Exception:
                pass
            cy += ch
            if i < num_children - 1 and cy < (y + height):
                cy += 1  # one-line spacing

class YHBoxCurses(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._height = 1  # HBox always takes one line
    
    def widgetClass(self):
        return "YHBox"
    
    def _create_backend_widget(self):
        self._backend_widget = None

    def _set_backend_enabled(self, enabled):
        """Enable/disable HBox and propagate to logical children."""
        try:
            for c in list(getattr(self, "_children", []) or []):
                try:
                    c.setEnabled(enabled)
                except Exception:
                    pass
        except Exception:
            pass

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

        remaining = max(0, available - fixed_total)
        if stretchables:
            per = remaining // len(stretchables)
            extra = remaining % len(stretchables)
            for k, idx in enumerate(stretchables):
                widths[idx] = max(1, per + (1 if k < extra else 0))
        else:
            if fixed_total < available:
                leftover = available - fixed_total
                per = leftover // num_children
                extra = leftover % num_children
                for i in range(num_children):
                    base = widths[i] if widths[i] else 1
                    widths[i] = base + per + (1 if i < extra else 0)

        # Draw children and pass full container height to stretchable children
        cx = x
        for i, child in enumerate(self._children):
            w = widths[i]
            if w <= 0:
                continue
            # If child is vertically stretchable, give full height; else give its minimum
            if child.stretchable(YUIDimension.YD_VERT):
                ch = height
            else:
                ch = min(height, getattr(child, "_height", height))
            if hasattr(child, "_draw"):
                child._draw(window, y, cx, w, ch)
            cx += w
            if i < num_children - 1:
                cx += 1

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

    def _set_backend_enabled(self, enabled):
        """Enable/disable label: labels are not focusable; just keep enabled state for drawing."""
        try:
            # labels don't accept focus; nothing to change except state used by draw
            # draw() will consult self._enabled from base class
            pass
        except Exception:
            pass

    def _draw(self, window, y, x, width, height):
        try:
            attr = 0
            if self._is_heading:
                attr |= curses.A_BOLD
            # dim if disabled
            if not self.isEnabled():
                attr |= curses.A_DIM

            # Truncate text to fit available width
            display_text = self._text[:max(0, width-1)]
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

    def _set_backend_enabled(self, enabled):
        """Enable/disable the input field: affect focusability and focused state."""
        try:
            # Save/restore _can_focus when toggling
            if not hasattr(self, "_saved_can_focus"):
                self._saved_can_focus = getattr(self, "_can_focus", True)
            if not enabled:
                # disable focusable behavior
                try:
                    self._saved_can_focus = self._can_focus
                except Exception:
                    self._saved_can_focus = False
                self._can_focus = False
                # if currently focused, remove focus
                if getattr(self, "_focused", False):
                    self._focused = False
            else:
                # restore previous focusability
                try:
                    self._can_focus = bool(getattr(self, "_saved_can_focus", True))
                except Exception:
                    self._can_focus = True
        except Exception:
            pass

    def _draw(self, window, y, x, width, height):
        try:
            # Draw label
            if self._label:
                label_text = self._label
                if len(label_text) > width // 3:
                    label_text = label_text[:width // 3]
                lbl_attr = curses.A_BOLD if self._is_heading else curses.A_NORMAL
                if not self.isEnabled():
                    lbl_attr |= curses.A_DIM
                window.addstr(y, x, label_text, lbl_attr)
                x += len(label_text) + 1
                width -= len(label_text) + 1

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
            if not self.isEnabled():
                attr = curses.A_DIM
            else:
                attr = curses.A_REVERSE if self._focused else curses.A_NORMAL

            field_bg = ' ' * width
            window.addstr(y, x, field_bg, attr)

            # Draw text
            if display_value:
                window.addstr(y, x, display_value, attr)

            # Show cursor if focused and enabled
            if self._focused and self.isEnabled():
                cursor_display_pos = min(self._cursor_pos, width - 1)
                if cursor_display_pos < len(display_value):
                    window.chgat(y, x + cursor_display_pos, 1, curses.A_REVERSE | curses.A_BOLD)
        except curses.error:
            pass

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled():
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

    def _set_backend_enabled(self, enabled):
        """Enable/disable push button: update focusability and collapse focus if disabling."""
        try:
            if not hasattr(self, "_saved_can_focus"):
                self._saved_can_focus = getattr(self, "_can_focus", True)
            if not enabled:
                try:
                    self._saved_can_focus = self._can_focus
                except Exception:
                    self._saved_can_focus = True
                self._can_focus = False
                if getattr(self, "_focused", False):
                    self._focused = False
            else:
                try:
                    self._can_focus = bool(getattr(self, "_saved_can_focus", True))
                except Exception:
                    self._can_focus = True
        except Exception:
            pass

    def _draw(self, window, y, x, width, height):
        try:
            # Center the button label within available width
            button_text = f"[ {self._label} ]"
            text_x = x + max(0, (width - len(button_text)) // 2)

            # Only draw if we have enough space
            if text_x + len(button_text) <= x + width:
                if not self.isEnabled():
                    attr = curses.A_DIM
                else:
                    attr = curses.A_REVERSE if self._focused else curses.A_NORMAL
                    if self._focused:
                        attr |= curses.A_BOLD

                window.addstr(y, text_x, button_text, attr)
        except curses.error:
            pass

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled():
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

    def _set_backend_enabled(self, enabled):
        """Enable/disable checkbox: update focusability and collapse focus if disabling."""
        try:
            if not hasattr(self, "_saved_can_focus"):
                self._saved_can_focus = getattr(self, "_can_focus", True)
            if not enabled:
                try:
                    self._saved_can_focus = self._can_focus
                except Exception:
                    self._saved_can_focus = True
                self._can_focus = False
                if getattr(self, "_focused", False):
                    self._focused = False
            else:
                try:
                    self._can_focus = bool(getattr(self, "_saved_can_focus", True))
                except Exception:
                    self._can_focus = True
        except Exception:
            pass

    def _draw(self, window, y, x, width, height):
        try:
            checkbox_symbol = "[X]" if self._is_checked else "[ ]"
            text = f"{checkbox_symbol} {self._label}"
            if len(text) > width:
                text = text[:max(0, width - 3)] + "..."

            if self._focused and self.isEnabled():
                window.attron(curses.A_REVERSE)
            elif not self.isEnabled():
                # indicate disabled with dim attribute
                window.attron(curses.A_DIM)

            window.addstr(y, x, text)

            if self._focused and self.isEnabled():
                window.attroff(curses.A_REVERSE)
            elif not self.isEnabled():
                try:
                    window.attroff(curses.A_DIM)
                except Exception:
                    pass
        except curses.error:
            pass

    def _handle_key(self, key):
        if not self.isEnabled():
            return False
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

    def _set_backend_enabled(self, enabled):
        """Enable/disable combobox: affect focusability, expanded state and focused state."""
        try:
            if not hasattr(self, "_saved_can_focus"):
                self._saved_can_focus = getattr(self, "_can_focus", True)
            if not enabled:
                try:
                    self._saved_can_focus = self._can_focus
                except Exception:
                    self._saved_can_focus = True
                self._can_focus = False
                # collapse expanded dropdown if any
                try:
                    if getattr(self, "_expanded", False):
                        self._expanded = False
                except Exception:
                    pass
                if getattr(self, "_focused", False):
                    self._focused = False
            else:
                try:
                    self._can_focus = bool(getattr(self, "_saved_can_focus", True))
                except Exception:
                    self._can_focus = True
        except Exception:
            pass

    def _draw(self, window, y, x, width, height):
        # Store position and dimensions for dropdown drawing
        self._combo_y = y
        self._combo_x = x
        self._combo_width = width

        try:
            # Calculate available space for combo box
            label_space = len(self._label) + 1 if self._label else 0
            combo_space = width - label_space

            if combo_space <= 3:
                return

            # Draw label
            if self._label:
                label_text = self._label
                if len(label_text) > label_space - 1:
                    label_text = label_text[:label_space - 1]
                lbl_attr = curses.A_NORMAL
                if not self.isEnabled():
                    lbl_attr |= curses.A_DIM
                window.addstr(y, x, label_text, lbl_attr)
                x += len(label_text) + 1

            # Prepare display value
            display_value = self._value if self._value else "Select..."
            max_display_width = combo_space - 3
            if len(display_value) > max_display_width:
                display_value = display_value[:max_display_width] + "..."

            # Draw combo box background
            if not self.isEnabled():
                attr = curses.A_DIM
            else:
                attr = curses.A_REVERSE if self._focused else curses.A_NORMAL

            combo_bg = " " * combo_space
            window.addstr(y, x, combo_bg, attr)

            combo_text = f" {display_value} ▼"
            if len(combo_text) > combo_space:
                combo_text = combo_text[:combo_space]

            window.addstr(y, x, combo_text, attr)

            # Draw expanded list if active and enabled
            if self._expanded and self.isEnabled():
                self._draw_expanded_list(window)
        except curses.error:
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
        if not self._focused or not self.isEnabled():
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

    def _set_backend_enabled(self, enabled):
        """Enable/disable selection box: affect focusability and propagate to row items."""
        try:
            if not hasattr(self, "_saved_can_focus"):
                self._saved_can_focus = getattr(self, "_can_focus", True)
            if not enabled:
                try:
                    self._saved_can_focus = self._can_focus
                except Exception:
                    self._saved_can_focus = True
                self._can_focus = False
                if getattr(self, "_focused", False):
                    self._focused = False
            else:
                try:
                    self._can_focus = bool(getattr(self, "_saved_can_focus", True))
                except Exception:
                    self._can_focus = True
            # propagate logical enabled state to contained items (if they are YWidget)
            try:
                for it in list(getattr(self, "_items", []) or []):
                    if hasattr(it, "setEnabled"):
                        try:
                            it.setEnabled(enabled)
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            pass

    def _draw(self, window, y, x, width, height):
        try:
            line = y
            # draw label if present
            if self._label:
                lbl = self._label
                lbl_attr = curses.A_BOLD
                if not self.isEnabled():
                    lbl_attr |= curses.A_DIM
                try:
                    window.addstr(line, x, lbl[:width], lbl_attr)
                except curses.error:
                    pass
                line += 1

            visible = self._visible_row_count()
            available_rows = max(0, height - (1 if self._label else 0))
            if self.stretchable(YUIDimension.YD_VERT):
                visible = min(len(self._items), available_rows)
            else:
                visible = min(len(self._items), self._visible_row_count(), available_rows)
            self._current_visible_rows = visible

            for i in range(visible):
                item_idx = self._scroll_offset + i
                if item_idx >= len(self._items):
                    break
                item = self._items[item_idx]
                text = item.label()
                checkbox = "*" if item in self._selected_items else " "
                display = f"[{checkbox}] {text}"
                if len(display) > width:
                    display = display[:max(0, width - 3)] + "..."
                attr = curses.A_NORMAL
                if not self.isEnabled():
                    attr |= curses.A_DIM
                if self._focused and item_idx == self._hover_index and self.isEnabled():
                    attr |= curses.A_REVERSE
                try:
                    window.addstr(line + i, x, display.ljust(width), attr)
                except curses.error:
                    pass

            if self._focused and len(self._items) > visible and width > 0 and self.isEnabled():
                try:
                    if self._scroll_offset > 0:
                        window.addch(y + (1 if self._label else 0), x + width - 1, '^')
                    if (self._scroll_offset + visible) < len(self._items):
                        window.addch(y + (1 if self._label else 0) + visible - 1, x + width - 1, 'v')
                except curses.error:
                    pass
        except curses.error:
            pass

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled():
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
    def __init__(self, parent=None, horAlign: YAlignmentType=YAlignmentType.YAlignUnchanged, vertAlign: YAlignmentType=YAlignmentType.YAlignUnchanged):
        super().__init__(parent)
        self._halign_spec = horAlign
        self._valign_spec = vertAlign
        self._backend_widget = None  # not used by curses
        self._height = 1

    def widgetClass(self):
        return "YAlignment"

    def stretchable(self, dim: YUIDimension):
        ''' Returns the stretchability of the layout box:
          * The layout box is stretchable if the child is stretchable in
          * this dimension or if the child widget has a layout weight in
          * this dimension.
        '''
        if self._child:
            expand = bool(self._child.stretchable(dim))
            weight = bool(self._child.weight(dim))
            if expand or weight:
                return True
        return False

    def addChild(self, child):
        try:
            super().addChild(child)
        except Exception:
            self._child = child
        # Ensure child is visible to traversal (dialog looks at widget._children)
        try:
            if not hasattr(self, "_children") or self._children is None:
                self._children = []
            if child not in self._children:
                self._children.append(child)
            # keep parent pointer consistent
            try:
                setattr(child, "_parent", self)
            except Exception:
                pass
        except Exception:
            pass

    def setChild(self, child):
        try:
            super().setChild(child)
        except Exception:
            self._child = child
        # Mirror to _children so focus traversal finds it
        try:
            if not hasattr(self, "_children") or self._children is None:
                self._children = []
            # replace existing children with this single child to avoid stale entries
            if self._children != [child]:
                self._children = [child]
            try:
                setattr(child, "_parent", self)
            except Exception:
                pass
        except Exception:
            pass

    def _create_backend_widget(self):
        self._backend_widget = None
        self._height = max(1, getattr(self._child, "_height", 1) if self._child else 1)

    def _set_backend_enabled(self, enabled):
        """Enable/disable alignment container and propagate to its logical child."""
        try:
            # propagate to logical child so it updates its own focusability/state
            child = getattr(self, "_child", None)
            if child is None:
                chs = getattr(self, "_children", None) or []
                child = chs[0] if chs else None
            if child is not None and hasattr(child, "setEnabled"):
                try:
                    child.setEnabled(enabled)
                except Exception:
                    pass
            # nothing else to do for curses backend (no real widget object)
        except Exception:
            pass

    def _child_min_width(self, child, max_width):
        # Heuristic minimal width similar to YHBoxCurses TODO: verify with widget information instead of hardcoded classes
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
            if self._halign_spec == YAlignmentType.YAlignEnd:
                cx = x + max(0, width - ch_min_w)
            elif self._halign_spec == YAlignmentType.YAlignCenter:
                cx = x + max(0, (width - ch_min_w) // 2)
            else:
                cx = x
            # Vertical position (single line widgets mostly)
            if self._valign_spec == YAlignmentType.YAlignCenter:
                cy = y + max(0, (height - 1) // 2)
            elif self._valign_spec == YAlignmentType.YAlignEnd:
                cy = y + max(0, height - 1)
            else:
                cy = y
            self._child._draw(window, cy, cx, min(ch_min_w, max(1, width)), min(height, getattr(self._child, "_height", 1)))
        except Exception:
            pass

class YTreeCurses(YSelectionWidget):
    """
    NCurses implementation of a tree widget.
    - Flattens visible nodes according to YTreeItem._is_open
    - Supports single/multi selection and recursive selection propagation
    - Preserves per-item selected() / setSelected() semantics and restores selections on rebuild
    - Keyboard: Up/Down/PageUp/PageDown/Home/End, SPACE = expand/collapse, ENTER = select/deselect
    """
    def __init__(self, parent=None, label="", multiselection=False, recursiveselection=False):
        super().__init__(parent)
        self._label = label
        self._multi = bool(multiselection)
        self._recursive = bool(recursiveselection)
        if self._recursive:
            self._multi = True
        self._immediate = self.notify()
        # Minimal height (items area) requested by this widget
        self._min_height = 6
        # Preferred height exposed to layout should include label line if any
        self._height = self._min_height + (1 if self._label else 0)
        self._can_focus = True
        self._focused = False
        self._hover_index = 0
        self._scroll_offset = 0
        self._visible_items = []
        self._selected_items = []
        self._last_selected_ids = set()
        self._suppress_selection_handler = False
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)

    def widgetClass(self):
        return "YTree"

    def hasMultiSelection(self):
        """Return True if the tree allows selecting multiple items at once."""
        return bool(self._multi)

    def immediateMode(self):
        return bool(self._immediate)

    def setImmediateMode(self, on:bool=True):
        self._immediate = on
        self.setNotify(on)

    def _create_backend_widget(self):
        # Keep preferred minimum for the layout (items + optional label)
        self._height = max(self._height, self._min_height + (1 if self._label else 0))
        self.rebuildTree()

    def addItem(self, item):
        """Ensure base storage gets the item and rebuild visible list immediately."""
        try:
            # prefer base implementation if present
            try:
                super().addItem(item)
            except Exception:
                # fallback: append to _items list used by this backend
                if not hasattr(self, "_items") or self._items is None:
                    self._items = []
                self._items.append(item)
        finally:
            try:
                # mark rebuild so new items are visible without waiting for external trigger
                self.rebuildTree()
            except Exception:
                pass

    def removeItem(self, item):
        """Remove item from internal list and rebuild."""
        try:
            try:
                super().removeItem(item)
            except Exception:
                if hasattr(self, "_items") and item in self._items:
                    try:
                        self._items.remove(item)
                    except Exception:
                        pass
        finally:
            try:
                self.rebuildTree()
            except Exception:
                pass

    def clearItems(self):
        """Clear items and rebuild."""
        try:
            try:
                super().clearItems()
            except Exception:
                self._items = []
        finally:
            try:
                self.rebuildTree()
            except Exception:
                pass

    def _collect_all_descendants(self, item):
        out = []
        stack = []
        try:
            for c in getattr(item, "_children", []) or []:
                stack.append(c)
        except Exception:
            pass
        while stack:
            cur = stack.pop()
            out.append(cur)
            try:
                for ch in getattr(cur, "_children", []) or []:
                    stack.append(ch)
            except Exception:
                pass
        return out

    def _flatten_visible(self):
        """Produce self._visible_items = [(item, depth), ...] following _is_open flags."""
        self._visible_items = []
        def _visit(nodes, depth=0):
            for n in nodes:
                self._visible_items.append((n, depth))
                try:
                    is_open = bool(getattr(n, "_is_open", False))
                except Exception:
                    is_open = False
                if is_open:
                    try:
                        childs = callable(getattr(n, "children", None)) and n.children() or getattr(n, "_children", []) or []
                    except Exception:
                        childs = getattr(n, "_children", []) or []
                    if childs:
                        _visit(childs, depth + 1)
        roots = list(getattr(self, "_items", []) or [])
        _visit(roots, 0)

    def rebuildTree(self):
        """Recompute visible items and restore selection from item.selected() or last_selected_ids."""
        # preserve items selection if any
        try:
            self._flatten_visible()
            # if there are previously saved last_selected_ids, prefer them
            selected_ids = set(self._last_selected_ids) if self._last_selected_ids else set()
            # if none, collect from items' selected() property
            if not selected_ids:
                try:
                    def _collect_selected(nodes):
                        out = []
                        for n in nodes:
                            try:
                                sel = False
                                if hasattr(n, "selected") and callable(getattr(n, "selected")):
                                    sel = n.selected()
                                else:
                                    sel = bool(getattr(n, "_selected", False))
                                if sel:
                                    out.append(n)
                            except Exception:
                                pass
                            try:
                                chs = callable(getattr(n, "children", None)) and n.children() or getattr(n, "_children", []) or []
                            except Exception:
                                chs = getattr(n, "_children", []) or []
                            if chs:
                                out.extend(_collect_selected(chs))
                        return out
                    pre_selected = _collect_selected(list(getattr(self, "_items", []) or []))
                    for p in pre_selected:
                        selected_ids.add(id(p))
                except Exception:
                    pass
            # build logical selected list and last_selected_ids
            sel_items = []
            for itm, _d in self._visible_items:
                try:
                    if id(itm) in selected_ids:
                        sel_items.append(itm)
                except Exception:
                    pass
            # also include non-visible selected nodes (descendants) if recursive selection used
            if selected_ids:
                try:
                    # scan full tree
                    def _all_nodes(nodes):
                        out = []
                        for n in nodes:
                            out.append(n)
                            try:
                                chs = callable(getattr(n, "children", None)) and n.children() or getattr(n, "_children", []) or []
                            except Exception:
                                chs = getattr(n, "_children", []) or []
                            if chs:
                                out.extend(_all_nodes(chs))
                        return out
                    all_nodes = _all_nodes(list(getattr(self, "_items", []) or []))
                    for n in all_nodes:
                        if id(n) in selected_ids and n not in sel_items:
                            sel_items.append(n)
                except Exception:
                    pass
            # apply selected flags to items consistently
            try:
                # clear all first
                def _clear(nodes):
                    for n in nodes:
                        try:
                            n.setSelected(False)
                        except Exception:
                            pass
                        try:
                            chs = callable(getattr(n, "children", None)) and n.children() or getattr(n, "_children", []) or []
                        except Exception:
                            chs = getattr(n, "_children", []) or []
                        if chs:
                            _clear(chs)
                _clear(list(getattr(self, "_items", []) or []))
            except Exception:
                pass
            for it in sel_items:
                try:
                    it.setSelected(True)
                except Exception:
                    pass
            self._selected_items = list(sel_items)
            self._last_selected_ids = set(id(i) for i in self._selected_items)
            # ensure hover_index valid
            if self._hover_index >= len(self._visible_items):
                self._hover_index = max(0, len(self._visible_items) - 1)
            self._ensure_hover_visible()
        except Exception:
            pass

    def _ensure_hover_visible(self, height=None):
        """Adjust scroll offset so hover visible in given height area (if None use last draw height)."""
        try:
            # height param is number of rows available for items display (excluding label)
            if height is None:
                height = max(1, getattr(self, "_height", 1))
            visible = max(1, height)
            if self._hover_index < self._scroll_offset:
                self._scroll_offset = self._hover_index
            elif self._hover_index >= self._scroll_offset + visible:
                self._scroll_offset = self._hover_index - visible + 1
        except Exception:
            pass

    def _toggle_expand(self, item):
        try:
            self._suppress_selection_handler = True
        except Exception:
            pass
        try:
            try:
                cur = item.isOpen()
                item.setOpen(not cur)
            except Exception:
                try:
                    cur = bool(getattr(item, "_is_open", False))
                    item._is_open = not cur
                except Exception:
                    pass
            # preserve selected ids and rebuild
            try:
                self._last_selected_ids = set(id(i) for i in getattr(self, "_selected_items", []) or [])
            except Exception:
                self._last_selected_ids = set()
            self.rebuildTree()
        finally:
            try:
                self._suppress_selection_handler = False
            except Exception:
                pass

    def _handle_selection_action(self, item):
        """Toggle selection (ENTER) respecting multi/single & recursive semantics."""
        if item is None:
            return
        try:
            if self._multi:
                # toggle membership
                if item in self._selected_items:
                    # deselect item and (if recursive) descendants
                    if self._recursive:
                        to_remove = {item} | set(self._collect_all_descendants(item))
                        self._selected_items = [it for it in self._selected_items if it not in to_remove]
                        for it in to_remove:
                            try:
                                it.setSelected(False)
                            except Exception:
                                try:
                                    setattr(it, "_selected", False)
                                except Exception:
                                    pass
                    else:
                        try:
                            self._selected_items.remove(item)
                        except Exception:
                            pass
                        try:
                            item.setSelected(False)
                        except Exception:
                            try:
                                setattr(item, "_selected", False)
                            except Exception:
                                pass
                else:
                    # select item and possibly descendants
                    if self._recursive:
                        to_add = [item] + self._collect_all_descendants(item)
                        for it in to_add:
                            if it not in self._selected_items:
                                self._selected_items.append(it)
                                try:
                                    it.setSelected(True)
                                except Exception:
                                    try:
                                        setattr(it, "_selected", True)
                                    except Exception:
                                        pass
                    else:
                        self._selected_items.append(item)
                        try:
                            item.setSelected(True)
                        except Exception:
                            try:
                                setattr(item, "_selected", True)
                            except Exception:
                                pass
            else:
                # single selection: clear all others and set this one
                try:
                    for it in list(getattr(self, "_items", []) or []):
                        try:
                            it.setSelected(False)
                        except Exception:
                            try:
                                setattr(it, "_selected", False)
                            except Exception:
                                pass
                except Exception:
                    pass
                self._selected_items = [item]
                try:
                    item.setSelected(True)
                except Exception:
                    try:
                        setattr(item, "_selected", True)
                    except Exception:
                        pass
        except Exception:
            pass

        # update last_selected_ids and notify
        try:
            self._last_selected_ids = set(id(i) for i in self._selected_items)
        except Exception:
            self._last_selected_ids = set()
        if self._immediate and self.notify():
            dlg = self.findDialog()
            if dlg:
                dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))

    def _draw(self, window, y, x, width, height):
        """Draw tree in provided rectangle. Expects height rows available."""
        try:
            # compute drawing area for items (first row may be label)
            line = y
            start_line = line
            label_rows = 1 if self._label else 0

            # Draw label
            if self._label:
                try:
                    window.addstr(line, x, self._label[:width], curses.A_BOLD)
                except curses.error:
                    pass
                line += 1

            # Actual rows given by parent for items
            available_rows = max(0, height - label_rows)
            # Keep _height as the current viewport rows (items area), not the preferred minimum
            self._height = max(1, available_rows)

            # record last draw height for navigation/ensure logic
            self._height = available_rows
            # rebuild visible items (safe cheap operation)
            self._flatten_visible()
            total = len(self._visible_items)
            if total == 0:
                try:
                    if available_rows > 0:
                        window.addstr(line, x, "(empty)", curses.A_DIM)
                except curses.error:
                    pass
                return

            # Clamp scroll/hover to the viewport
            self._ensure_hover_visible(height=self._height)

            # Draw only inside the allocated rectangle
            draw_rows = min(available_rows, max(0, total - self._scroll_offset))
            for i in range(draw_rows):
                idx = self._scroll_offset + i
                if idx >= total:
                    break
                itm, depth = self._visible_items[idx]
                is_selected = itm in self._selected_items
                # expander, text, attrs...
                try:
                    has_children = bool(getattr(itm, "_children", []) or (callable(getattr(itm, "children", None)) and (itm.children() or [])))
                except Exception:
                    has_children = False
                try:
                    is_open = bool(getattr(itm, "_is_open", False))
                except Exception:
                    is_open = False
                exp = "▾" if (has_children and is_open) else ("▸" if has_children else " ")
                checkbox = "*" if is_selected else " "
                indent = " " * (depth * 2)
                text = f"{indent}{exp} [{checkbox}] {itm.label()}"
                if len(text) > width:
                    text = text[:max(0, width - 3)] + "..."
                attr = curses.A_REVERSE if (self._focused and idx == self._hover_index and self.isEnabled()) else curses.A_NORMAL
                if not self.isEnabled():
                    attr |= curses.A_DIM
                try:
                    window.addstr(line + i, x, text.ljust(width), attr)
                except curses.error:
                    pass

            # Scroll indicators based on actual viewport rows
            try:
                if self._scroll_offset > 0 and available_rows > 0:
                    window.addch(y + label_rows, x + max(0, width - 1), '^')
                if (self._scroll_offset + available_rows) < total and available_rows > 0:
                    window.addch(y + label_rows + min(available_rows - 1, total - 1), x + max(0, width - 1), 'v')
            except curses.error:
                pass
        except Exception:
            pass

    def _handle_key(self, key):
        """Keyboard handling: navigation, expand (SPACE), select (ENTER)."""
        if not self._focused or not self.isEnabled():
            return False
        handled = True
        total = len(self._visible_items)
        if key == curses.KEY_UP:
            if self._hover_index > 0:
                self._hover_index -= 1
                self._ensure_hover_visible(self._height)
        elif key == curses.KEY_DOWN:
            if self._hover_index < max(0, total - 1):
                self._hover_index += 1
                self._ensure_hover_visible(self._height)
        elif key == curses.KEY_PPAGE:
            step = max(1, self._height)
            self._hover_index = max(0, self._hover_index - step)
            self._ensure_hover_visible(self._height)
        elif key == curses.KEY_NPAGE:
            step = max(1, self._height)
            self._hover_index = min(max(0, total - 1), self._hover_index + step)
            self._ensure_hover_visible(self._height)
        elif key == curses.KEY_HOME:
            self._hover_index = 0
            self._ensure_hover_visible(self._height)
        elif key == curses.KEY_END:
            self._hover_index = max(0, total - 1)
            self._ensure_hover_visible(self._height)
        elif key in (ord(' '),):  # SPACE toggles expansion per dialog footer convention
            if 0 <= self._hover_index < total:
                itm, _ = self._visible_items[self._hover_index]
                # Toggle expand/collapse without changing selection
                self._toggle_expand(itm)
        elif key in (ord('\n'),):  # ENTER toggles selection
            if 0 <= self._hover_index < total:
                itm, _ = self._visible_items[self._hover_index]
                self._handle_selection_action(itm)
        else:
            handled = False
        return handled

    def currentItem(self):
        try:
            # Prefer explicit selected_items; if empty return hovered visible item (useful after selection)
            if self._selected_items:
                return self._selected_items[0]
            # fallback: return hovered visible item if any
            if 0 <= self._hover_index < len(getattr(self, "_visible_items", [])):
                return self._visible_items[self._hover_index][0]
            return None
        except Exception:
            return None

    def getSelectedItems(self):
        return list(self._selected_items)

    def selectItem(self, item, selected=True):
        """Programmatic select/deselect that respects recursive flag."""
        if item is None:
            return
        try:
            if selected:
                if not self._multi:
                    # clear others
                    try:
                        for it in list(getattr(self, "_items", []) or []):
                            try:
                                it.setSelected(False)
                            except Exception:
                                try:
                                    setattr(it, "_selected", False)
                                except Exception:
                                    pass
                        item.setSelected(True)
                    except Exception:
                        try:
                            setattr(item, "_selected", True)
                        except Exception:
                            pass
                    self._selected_items = [item]
                else:
                    if item not in self._selected_items:
                        try:
                            item.setSelected(True)
                        except Exception:
                            try:
                                setattr(item, "_selected", True)
                            except Exception:
                                pass
                        self._selected_items.append(item)
                    if self._recursive:
                        for d in self._collect_all_descendants(item):
                            if d not in self._selected_items:
                                try:
                                    d.setSelected(True)
                                except Exception:
                                    try:
                                        setattr(d, "_selected", True)
                                    except Exception:
                                        pass
                                self._selected_items.append(d)
            else:
                # deselect
                if item in self._selected_items:
                    try:
                        self._selected_items.remove(item)
                    except Exception:
                        pass
                try:
                    item.setSelected(False)
                except Exception:
                    try:
                        setattr(item, "_selected", False)
                    except Exception:
                        pass
                if self._recursive:
                    for d in self._collect_all_descendants(item):
                        if d in self._selected_items:
                            try:
                                self._selected_items.remove(d)
                            except Exception:
                                pass
                        try:
                            d.setSelected(False)
                        except Exception:
                            try:
                                setattr(d, "_selected", False)
                            except Exception:
                                pass
            # update last ids
            try:
                self._last_selected_ids = set(id(i) for i in self._selected_items)
            except Exception:
                self._last_selected_ids = set()
        except Exception:
            pass
