# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains all Qt backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''
from PySide6 import QtWidgets, QtGui
import os
import logging
from ...yui_common import *


__all__ = ["_resolve_icon"]

def _resolve_icon(icon_name):
    """Resolve an icon name to a QtGui.QIcon or None.

    - If icon_name is an existing absolute or relative path -> load from path.
    - If icon_name contains a path separator or exists on filesystem -> treat as path.
    - Otherwise strip extension (if any) and try QIcon.fromTheme, then fallback to QIcon(name).
    """
    try:
        if not icon_name:
            return None
        logger = logging.getLogger(f"manatools.aui.qt.common")
        # If icon_name looks like a filesystem path (absolute or contains a
        # path separator), prefer loading from disk. If it has no
        # extension, also try the same path with a .png suffix to help
        # debugging/test cases where a directory+basename is provided.
        # Only treat as a filesystem path when the name is absolute or contains
        # a path separator.  Bare names like "isodumper" are theme-icon names
        # and must NOT be probed on disk — the CWD may contain a launcher
        # script with the same name (e.g. isodumper/isodumper), which would
        # cause QIcon to silently load a binary file instead of the theme icon.
        is_file_path = os.path.isabs(icon_name) or os.sep in icon_name
        try:
            if is_file_path:
                if os.path.isfile(icon_name):
                    return QtGui.QIcon(icon_name)
                # no extension → also try .png suffix
                base, ext = os.path.splitext(icon_name)
                if not ext:
                    png_candidate = icon_name + '.png'
                    if os.path.isfile(png_candidate):
                        logger.debug("Resolved icon %r to %r", icon_name, png_candidate)
                        return QtGui.QIcon(png_candidate)
                # not found on filesystem: fall through to theme lookup
            else:
                # Bare name with an explicit extension can still be a relative
                # file reference (e.g. "logo.png" in the same directory).
                # Bare names without an extension are always theme-icon names.
                if "." in icon_name and os.path.isfile(icon_name):
                    logger.debug("Resolved icon %r to relative filesystem path", icon_name)
                    return QtGui.QIcon(icon_name)
        except Exception:
            pass
        base = icon_name
        try:
            if "." in base:
                base = os.path.splitext(base)[0]
        except Exception:
            pass
        try:
            logger.debug("Trying to resolve icon %r via QIcon.fromTheme(%r)", icon_name, base)
            ico = QtGui.QIcon.fromTheme(base)
            if ico and not ico.isNull():
                logger.debug("Resolved icon %r to theme icon %r", icon_name, base)
                return ico
        except Exception:
            pass
        try:
            ico = QtGui.QIcon(icon_name)
            if ico and not ico.isNull():
                logger.debug("Resolved icon %r to QIcon(%r)", icon_name, icon_name)
                return ico
        except Exception:
            pass
    except Exception:
        pass
    return None