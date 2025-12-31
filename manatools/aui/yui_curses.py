"""
NCurses backend implementation for YUI
"""

import curses
import curses.ascii
import sys
import os
import time
from .yui_common import *
from .backends.curses import *

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
        self._product_name = "manatools AUI Curses"
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
    def createIntField(self, parent, label, minVal, maxVal, initialVal):
        return YIntFieldCurses(parent, label, minVal, maxVal, initialVal)
    
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
 
    def createFrame(self, parent, label: str=""):
        """Create a Frame widget."""
        return YFrameCurses(parent, label)

    def createCheckBoxFrame(self, parent, label: str = "", checked: bool = False):
        """Create a CheckBox Frame widget."""
        return YCheckBoxFrameCurses(parent, label, checked)
    
    def createProgressBar(self, parent, label, max_value=100):
        """Create a Progress Bar widget."""
        return YProgressBarCurses(parent, label, max_value)

    def createRadioButton(self, parent, label="", isChecked=False):
        """Create a Radio Button widget."""
        return YRadioButtonCurses(parent, label, isChecked)

    def createTable(self, parent, header: YTableHeader, multiSelection=False):
        """Create a Table widget (curses backend)."""
        return YTableCurses(parent, header, multiSelection)

    def createRichText(self, parent, text: str = "", plainTextMode: bool = False):
        """Create a RichText widget (curses backend)."""
        return YRichTextCurses(parent, text, plainTextMode)

    def createMenuBar(self, parent):
        """Create a MenuBar widget (curses backend)."""
        return YMenuBarCurses(parent)

    def createReplacePoint(self, parent):
        """Create a ReplacePoint widget (curses backend)."""
        return YReplacePointCurses(parent)