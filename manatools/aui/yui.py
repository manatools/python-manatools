#!/usr/bin/env python3
"""
Unified YUI implementation that automatically selects the best available backend.
Priority: Qt > GTK > NCurses
"""

import os
import sys
from enum import Enum

class Backend(Enum):
    QT = "qt"
    GTK = "gtk" 
    NCURSES = "ncurses"

class YUI:
    _instance = None
    _backend = None
    
    @classmethod
    def _detect_backend(cls):
        """Detect the best available backend"""
        # Check environment variable first
        backend_env = os.environ.get('YUI_BACKEND', '').lower()
        if backend_env == 'qt':
            return Backend.QT
        elif backend_env == 'gtk':
            return Backend.GTK
        elif backend_env == 'ncurses':
            return Backend.NCURSES
        
        # Auto-detect based on available imports
        # Require PySide6 (Qt6)
        try:
            import PySide6.QtWidgets
            return Backend.QT
        except ImportError:
            pass

        # GTK: require GTK4
        try:
            import gi
            gi.require_version('Gtk', '4.0')
            from gi.repository import Gtk
            return Backend.GTK
        except (ImportError, ValueError):
            pass
            
        try:
            import curses
            return Backend.NCURSES
        except ImportError:
            pass
            
        raise RuntimeError("No UI backend available. Install PySide6, PyGObject (GTK4), or curses.")
    
    @classmethod
    def ui(cls):
        if cls._instance is None:
            cls._backend = cls._detect_backend()
            print(f"Detected backend: {cls._backend}")
            
            if cls._backend == Backend.QT:
                from .yui_qt import YUIQt as YUIImpl
            elif cls._backend == Backend.GTK:
                from .yui_gtk import YUIGtk as YUIImpl
            elif cls._backend == Backend.NCURSES:
                from .yui_curses import YUICurses as YUIImpl
            else:
                raise RuntimeError(f"Unknown backend: {cls._backend}")
                
            cls._instance = YUIImpl()
            
        return cls._instance
    
    @classmethod
    def backend(cls):
        if cls._instance is None:
            cls.ui()  # This will detect the backend
        return cls._backend
    
    @classmethod
    def widgetFactory(cls):
        return cls.ui().widgetFactory()
    
    @classmethod
    def optionalWidgetFactory(cls):
        return cls.ui().optionalWidgetFactory()
    
    @classmethod
    def app(cls):
        return cls.ui().app()
    
    @classmethod
    def application(cls):
        return cls.ui().application()
    
    @classmethod
    def yApp(cls):
        return cls.ui().yApp()

# Global functions for compatibility with libyui API
def YUI_ui():
    return YUI.ui()

def YUI_widgetFactory():
    return YUI.widgetFactory()

def YUI_optionalWidgetFactory():
    return YUI.optionalWidgetFactory()

def YUI_app():
    return YUI.app()

def YUI_application():
    return YUI.application()

def YUI_yApp():
    return YUI.yApp()

def YUI_ensureUICreated():
    return YUI.ui()

# Import common classes that are backend-agnostic
from .yui_common import (
    # Enums
    YUIDimension, YAlignmentType, YDialogType, YDialogColorMode,
    YEventType, YEventReason, YCheckBoxState, YButtonRole,
    # Base classes
    YWidget, YSingleChildContainerWidget, YSelectionWidget,
    YSimpleInputField, YItem, YTreeItem,
    # Events
    YEvent, YWidgetEvent, YKeyEvent, YMenuEvent, YCancelEvent,
    # Exceptions
    YUIException, YUIWidgetNotFoundException, YUINoDialogException,
    # Other common classes
    YProperty, YPropertyValue, YPropertySet, YShortcut
)

# Re-export everything for easy importing
__all__ = [
    'YUI', 'YUI_ui', 'YUI_widgetFactory', 'YUI_app', 'YUI_application', 'YUI_yApp',
    'YUIDimension', 'YAlignmentType', 'YDialogType', 'YDialogColorMode',
    'YEventType', 'YEventReason', 'YCheckBoxState', 'YButtonRole',
    'YWidget', 'YSingleChildContainerWidget', 'YSelectionWidget', 
    'YSimpleInputField', 'YItem', 'YTreeItem',
    'YEvent', 'YWidgetEvent', 'YKeyEvent', 'YMenuEvent', 'YCancelEvent',
    'YUIException', 'YUIWidgetNotFoundException', 'YUINoDialogException',
    'YProperty', 'YPropertyValue', 'YPropertySet', 'YShortcut',
    'Backend'
]