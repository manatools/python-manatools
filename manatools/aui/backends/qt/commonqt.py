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
        # If icon_name looks like a filesystem path (absolute or contains a
        # path separator), prefer loading from disk. If it has no
        # extension, also try the same path with a .png suffix to help
        # debugging/test cases where a directory+basename is provided.
        try:
            if os.path.isabs(icon_name) or os.path.sep in icon_name:
                # exact file
                if os.path.exists(icon_name):
                    return QtGui.QIcon(icon_name)
                # if there's no extension, try .png
                base, ext = os.path.splitext(icon_name)
                if not ext:
                    png_candidate = icon_name + '.png'
                    if os.path.exists(png_candidate):
                        return QtGui.QIcon(png_candidate)
                # not found on filesystem: fall through to theme/name
            else:
                # non-path might still be a relative file name
                if os.path.exists(icon_name):
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
            ico = QtGui.QIcon.fromTheme(base)
            if ico and not ico.isNull():
                return ico
        except Exception:
            pass
        try:
            ico = QtGui.QIcon(icon_name)
            if ico and not ico.isNull():
                return ico
        except Exception:
            pass
    except Exception:
        pass
    return None