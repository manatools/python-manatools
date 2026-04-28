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
        """Detect the best available backend.

        Priority:
        1. MUI_BACKEND environment variable (user override).
        2. XDG_CURRENT_DESKTOP present → desktop session:
           - Known GTK desktops  → try GTK4, warn + try Qt if unavailable.
           - Everything else     → try Qt, warn + try GTK4 if unavailable.
           In both cases NCurses is the last resort for graphical sessions.
        3. DISPLAY or WAYLAND_DISPLAY present but XDG_CURRENT_DESKTOP absent
           (e.g. after «su -»): try Qt then GTK4, fall back to NCurses.
        4. PKEXEC_UID present (app launched via pkexec/polkit): recover display
           access by detecting live sockets in the filesystem
           (/run/user/<uid>/ for Wayland, /tmp/.X11-unix/ for X11), inject the
           minimum required variables into the environment, then try graphical
           backends before falling back to NCurses.
           Inspired by the Anaconda liveinst recovery pattern
           (data/liveinst/liveinst lines 81-108).
        5. No display available → headless / TTY → NCurses only.

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

        # ── 3. Display server available but no XDG desktop (e.g. after su -) ──
        # DISPLAY or WAYLAND_DISPLAY is set, so a graphical session is reachable
        # even though XDG_CURRENT_DESKTOP was not inherited.  Try graphical
        # backends before falling back to NCurses.
        _display_env = os.environ.get('WAYLAND_DISPLAY') or os.environ.get('DISPLAY')
        if _display_env:
            _log.warning(
                "XDG_CURRENT_DESKTOP not set but a display server is available "
                "(%s) — trying graphical backends.",
                'WAYLAND_DISPLAY' if os.environ.get('WAYLAND_DISPLAY') else 'DISPLAY',
            )
            if _try_qt():
                return Backend.QT
            if _try_gtk():
                return Backend.GTK
            _log.warning(
                "No graphical backend available despite display server "
                "— falling back to NCurses."
            )
            if _try_ncurses():
                return Backend.NCURSES
            raise RuntimeError(
                "No UI backend available: Qt and GTK4 are both missing, "
                "and curses is not installed."
            )

        # ── 4. pkexec context: recover display access from the filesystem ──
        # pkexec strips the environment, including DISPLAY, WAYLAND_DISPLAY and
        # XDG_CURRENT_DESKTOP.  PKEXEC_UID is the one variable pkexec always
        # preserves; from it we can locate the original user's XDG_RUNTIME_DIR
        # and search for a live Wayland or X11 socket.
        #
        # Security notes:
        #   • PKEXEC_UID is validated as a plain non-negative integer before
        #     being used in any path construction (prevents directory traversal).
        #   • Every candidate socket is verified with os.stat + S_ISSOCK so that
        #     a regular file planted at the expected path is rejected.
        #   • X11 display numbers are validated as integers (e.g. «X0» → «:0»).
        #   • Only DISPLAY, WAYLAND_DISPLAY, and XDG_RUNTIME_DIR are written to
        #     os.environ; no arbitrary data from the filesystem is exported.
        #   • No subprocess is spawned; no shell interpolation takes place.
        _pkexec_uid_str = os.environ.get('PKEXEC_UID', '')
        if _pkexec_uid_str:
            _uid = None
            try:
                _uid = int(_pkexec_uid_str)
                if _uid < 0:
                    raise ValueError("negative UID")
            except ValueError:
                _log.warning("PKEXEC_UID is not a valid non-negative integer (%r) — skipping pkexec recovery.",
                             _pkexec_uid_str)

            if _uid is not None:
                import stat as _stat
                _runtime_dir = f'/run/user/{_uid}'
                _wayland_name = None
                _x11_display  = None

                # Prefer Wayland: look for wayland-* sockets in the user's
                # XDG_RUNTIME_DIR (typically /run/user/<uid>/).
                if os.path.isdir(_runtime_dir):
                    try:
                        for _name in sorted(os.listdir(_runtime_dir)):
                            if _name.startswith('wayland-') and not _name.endswith('.lock'):
                                _path = os.path.join(_runtime_dir, _name)
                                try:
                                    if _stat.S_ISSOCK(os.stat(_path).st_mode):
                                        _wayland_name = _name
                                        break
                                except OSError:
                                    pass
                    except OSError:
                        pass

                # Fall back to X11: look for X<n> sockets in /tmp/.X11-unix/.
                if not _wayland_name:
                    _x11_dir = '/tmp/.X11-unix'
                    if os.path.isdir(_x11_dir):
                        try:
                            for _name in sorted(os.listdir(_x11_dir)):
                                if _name.startswith('X'):
                                    try:
                                        _num  = int(_name[1:])   # must be digits only
                                        _path = os.path.join(_x11_dir, _name)
                                        if _stat.S_ISSOCK(os.stat(_path).st_mode):
                                            _x11_display = f':{_num}'
                                            break
                                    except (ValueError, OSError):
                                        pass
                        except OSError:
                            pass

                if _wayland_name or _x11_display:
                    # Inject only the variables needed to connect to the
                    # display server; nothing else from the filesystem is exported.
                    os.environ['XDG_RUNTIME_DIR'] = _runtime_dir
                    if _wayland_name:
                        os.environ['WAYLAND_DISPLAY'] = _wayland_name
                        _display_info = f'WAYLAND_DISPLAY={_wayland_name}'
                    else:
                        os.environ['DISPLAY'] = _x11_display
                        _display_info = f'DISPLAY={_x11_display}'

                    _log.info(
                        "pkexec context (PKEXEC_UID=%d): recovered %s from "
                        "filesystem — trying graphical backends.", _uid, _display_info
                    )
                    if _try_qt():
                        return Backend.QT
                    if _try_gtk():
                        return Backend.GTK
                    _log.warning(
                        "pkexec context: no graphical backend available "
                        "despite display server — falling back to NCurses."
                    )
                else:
                    _log.info(
                        "pkexec context (PKEXEC_UID=%d): no display socket found "
                        "— falling back to NCurses.", _uid
                    )

        # ── 5. No desktop, no display → headless / TTY → NCurses ──────────
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