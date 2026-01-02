# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Common helpers for the curses backend.

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.curses
'''
import logging
from ...yui_common import YUIDimension

__all__ = ["pixels_to_chars"]

_logger = logging.getLogger("manatools.aui.curses.common")

def pixels_to_chars(size_px: float, dim: YUIDimension) -> int:
    """Convert a pixel size into character cells for curses.

    Mapping rationale: libyui uses an abstract unit where a main window of
    800x600 pixels corresponds to an 80x25 character window. We adopt the same
    ratio: 10 px per column horizontally, 24 px per row vertically.

    This conversion provides a uniform interpretation of the `size` argument
    across Qt/GTK/curses backends.
    """
    try:
        px = max(0.0, float(size_px))
    except Exception:
        px = 0.0
    if dim == YUIDimension.YD_HORIZ:
        return max(0, int(round(px / 10.0)))
    else:
        return max(0, int(round(px / 24.0)))
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

# Module-level logger for common curses helpers
_mod_logger = logging.getLogger("manatools.aui.curses.common.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)

__all__ = ["_curses_recursive_min_height"]


def _curses_recursive_min_height(widget):
    """Compute minimal height for a widget, recursively considering container children."""
    if widget is None:
        return 1
    try:
        cls = widget.widgetClass() if hasattr(widget, "widgetClass") else ""
    except Exception:
        cls = ""
    try:
        if cls == "YVBox":
            chs = list(getattr(widget, "_children", []) or [])
            spacing = max(0, len(chs) - 1)
            total = 0
            for c in chs:
                total += _curses_recursive_min_height(c)
            return max(1, total + spacing)
        elif cls == "YHBox":
            chs = list(getattr(widget, "_children", []) or [])
            tallest = 1
            for c in chs:
                tallest = max(tallest, _curses_recursive_min_height(c))
            return max(1, tallest)
        elif cls == "YAlignment":
            child = widget.child()
            return max(1, _curses_recursive_min_height(child))
        elif cls == "YReplacePoint":
            # Treat ReplacePoint as a transparent single-child container
            child = widget.child()
            return max(1, _curses_recursive_min_height(child))
        elif cls == "YFrame" or cls == "YCheckBoxFrame":
            child = widget.child()
            inner_top = max(0, getattr(widget, "_inner_top_padding", 1))
            inner_min = _curses_recursive_min_height(child)
            return max(3, 2 + inner_top + inner_min)  # borders(2) + padding + inner
        else:
            return max(1, getattr(widget, "_height", 1))
    except Exception as e:
        try:
            _mod_logger.error("_curses_recursive_min_height error: %s", e, exc_info=True)
        except Exception:
            pass
        return max(1, getattr(widget, "_height", 1))
