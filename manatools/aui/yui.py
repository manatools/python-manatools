#!/usr/bin/env python3
"""
Unified YUI implementation that automatically selects the best available backend.
Priority: Qt > GTK > NCurses > Web (Web requires explicit selection)
"""

import os
import sys
from enum import Enum

class Backend(Enum):
    QT = "qt"
    GTK = "gtk" 
    NCURSES = "ncurses"
    WEB = "web"

class YUI:
    _instance = None
    _backend = None
    
    @classmethod
    def _detect_backend(cls):
        """Detect the best available backend.

        Priority:
        1. MUI_BACKEND environment variable (user override).
        2. XDG_CURRENT_DESKTOP present → desktop session:
           - Known GTK desktops  → try GTK4, warn + try Qt if unavailable.
           - Everything else     → try Qt, warn + try GTK4 if unavailable.
           In both cases NCurses is the last resort for graphical sessions.
        3. No desktop session → NCurses only.

        A RuntimeError is raised only when every candidate backend is missing.
        Import probes are deferred: only the library actually needed is probed.
        """
        import logging
        _log = logging.getLogger(__name__)

        # ── helpers ────────────────────────────────────────────────────────
        def _try_gtk():
            try:
                import gi
                gi.require_version('Gtk', '4.0')
                from gi.repository import Gtk  # noqa: F401
                return True
            except (ImportError, ValueError):
                return False

        def _try_qt():
            try:
                import PySide6.QtWidgets  # noqa: F401
                return True
            except ImportError:
                return False

        def _try_ncurses():
            try:
                import curses  # noqa: F401
                return True
            except ImportError:
                return False

        # ── 1. Explicit user override — no probing needed ──────────────────
        backend_env = os.environ.get('MUI_BACKEND', '').lower()
        if backend_env == 'qt':
            return Backend.QT
        if backend_env == 'gtk':
            return Backend.GTK
        if backend_env == 'ncurses':
            return Backend.NCURSES
        if backend_env == 'web':
            return Backend.WEB

        # Auto-detect based on available imports
        # Require PySide6 (Qt6)
        try:
            import PySide6.QtWidgets
            return Backend.QT
        except ImportError:
            pass

        # ── 2. Desktop session present ─────────────────────────────────────
        xdg = os.environ.get('XDG_CURRENT_DESKTOP', '')
        if xdg:
            # XDG spec allows colon-separated stacking (e.g. "ubuntu:GNOME")
            desktops = {d.strip().upper() for d in xdg.split(':')}
            _GTK_DESKTOPS = {
                'GNOME', 'XFCE', 'MATE', 'LXDE', 'CINNAMON',
                'PANTHEON', 'UNITY', 'ENLIGHTENMENT', 'SUGAR',
            }

            if desktops & _GTK_DESKTOPS:
                # GTK-preferred desktop
                if _try_gtk():
                    return Backend.GTK
                matched = ', '.join(sorted(desktops & _GTK_DESKTOPS))
                _log.warning(
                    "GTK desktop detected (%s) but GTK4 (python-gobject/gi) "
                    "is not available — trying Qt as fallback.", matched
                )
                if _try_qt():
                    return Backend.QT
                _log.warning(
                    "PySide6 (Qt) not available either — falling back to NCurses."
                )
            else:
                # Qt-preferred desktop
                if _try_qt():
                    return Backend.QT
                desktop_names = ', '.join(sorted(desktops))
                _log.warning(
                    "Qt desktop detected (%s) but PySide6 is not available "
                    "— trying GTK4 as fallback.", desktop_names
                )
                if _try_gtk():
                    return Backend.GTK
                _log.warning(
                    "GTK4 not available either — falling back to NCurses."
                )

            # Last resort even for graphical sessions
            if _try_ncurses():
                return Backend.NCURSES
            raise RuntimeError(
                "No UI backend available: Qt, GTK4, and NCurses are all missing."
            )

        # ── 3. No desktop → headless / TTY → NCurses ──────────────────────
        if _try_ncurses():
            return Backend.NCURSES
        raise RuntimeError(
            "No UI backend available: running headless but curses is not installed."
        )
    
    @classmethod
    def ui(cls):
        if cls._instance is None:
            cls._backend = cls._detect_backend()
            import logging as _log
            _log.getLogger(__name__).info("Selected UI backend: %s", cls._backend)

            _backend_map = {
                Backend.QT:      ('.yui_qt',     'YUIQt'),
                Backend.GTK:     ('.yui_gtk',    'YUIGtk'),
                Backend.NCURSES: ('.yui_curses', 'YUICurses'),
                Backend.WEB: ('.yui_web0, 'YUIWeb'),
            }
            if cls._backend not in _backend_map:
                raise RuntimeError(f"Unknown backend: {cls._backend}")

            module_path, class_name = _backend_map[cls._backend]
            try:
                import importlib as _imp
                _mod = _imp.import_module(module_path, package=__package__)
                YUIImpl = getattr(_mod, class_name)
            except ImportError as exc:
                # Safety net: backend module failed to import despite passing the
                # probe in _detect_backend (e.g. GTK version locked by a 3rd-party
                # library between detection and import).  Reset state and re-raise
                # so the caller can retry with a different backend override.
                _log.getLogger(__name__).error(
                    "Backend %s import failed (%s); "
                    "set MUI_BACKEND env var to force a different backend.",
                    cls._backend, exc,
                )
                cls._backend = None
                cls._instance = None
                raise

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
    YEventType, YEventReason, YCheckBoxState, YButtonRole, YLogViewFocus,
    # Base classes
    YWidget, YSingleChildContainerWidget, YSelectionWidget,
    YSimpleInputField, YItem, YTreeItem, YTableHeader, YTableItem, YTableCell,
    # Events
    YEvent, YWidgetEvent, YKeyEvent, YMenuEvent, YTimeoutEvent, YCancelEvent,
    # Exceptions
    YUIException, YUIWidgetNotFoundException, YUINoDialogException, YUIInvalidWidgetException,
    # Menu model
    YMenuItem,
    # Property system
    YPropertyType, YProperty, YPropertyValue, YPropertySet, YShortcut
)

# Re-export everything for easy importing
__all__ = [
    'YUI', 'YUI_ui', 'YUI_widgetFactory', 'YUI_app', 'YUI_application', 'YUI_yApp',
    'YUIDimension', 'YAlignmentType', 'YDialogType', 'YDialogColorMode',
    'YEventType', 'YEventReason', 'YCheckBoxState', 'YButtonRole', 'YLogViewFocus',
    'YWidget', 'YSingleChildContainerWidget', 'YSelectionWidget', 
    'YSimpleInputField', 'YItem', 'YTreeItem', 'YTableHeader', 'YTableItem', 'YTableCell',
    'YEvent', 'YWidgetEvent', 'YKeyEvent', 'YMenuEvent', 'YTimeoutEvent', 'YCancelEvent',
    'YUIException', 'YUIWidgetNotFoundException', 'YUINoDialogException', 'YUIInvalidWidgetException',
    'YMenuItem',
    'YPropertyType', 'YProperty', 'YPropertyValue', 'YPropertySet', 'YShortcut',
    'Backend'
]
