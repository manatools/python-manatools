# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Common helpers for the curses backend.

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

__all__ = ["pixels_to_chars", "_curses_recursive_min_height", "_curses_recursive_min_width"]

# Module-level logger for common curses helpers
_mod_logger = logging.getLogger("manatools.aui.curses.common")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)

def pixels_to_chars(size_px: int, dim: YUIDimension) -> int:
    """Convert a pixel size into terminal character cells.

    Horizontal (X): 1 character = 8 pixels (i.e., 1 pixel = 0.125 char).
    Vertical (Y): assumed 1 character row ≈ 16 pixels (typical terminal font).

    The vertical ratio can be adjusted later if needed; this maps pixel sizes
    to curses units uniformly with Qt/GTK which operate in pixels.
    """
    try:
        px = max(0, int(size_px))
    except Exception:
        px = 0
    if dim == YUIDimension.YD_HORIZ:
        return max(0, int(round(px / 8.0)))
    else:
        return max(0, int(round(px / 16.0)))

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


def _curses_recursive_min_width(widget):
    """Compute minimal width for a widget, recursively considering container children.

    Heuristics:
    - YHBox: sum of children's minimal widths plus 1 char spacing between them
    - YVBox: maximal minimal width among children
    - Frames (YFrame/YCheckBoxFrame): border (2) + inner minimal width
    - Alignment/ReplacePoint: pass-through to child
    - Basic widgets: use `minWidth()` if available, otherwise infer from text/label
    """
    try:
        if widget is None:
            return 1
        cls = widget.widgetClass() if hasattr(widget, "widgetClass") else ""
        # Helper to infer min width of leaf/basic widgets
        def _leaf_min_width(w):
            try:
                if hasattr(w, "minWidth"):
                    m = int(w.minWidth())
                    return max(1, m)
            except Exception:
                pass
            try:
                c = w.widgetClass() if hasattr(w, "widgetClass") else ""
                if c in ("YLabel", "YPushButton", "YCheckBox"):
                    text = getattr(w, "_text", None)
                    if text is None:
                        text = getattr(w, "_label", "")
                    pad = 4 if c == "YPushButton" else 0
                    # Checkbox includes symbol like "[ ] "
                    if c == "YCheckBox":
                        pad = max(pad, 4)
                    return max(1, len(str(text)) + pad)
            except Exception:
                pass
            try:
                return max(1, int(getattr(w, "_width", 10)))
            except Exception:
                return 10

        if cls == "YHBox":
            chs = list(getattr(widget, "_children", []) or [])
            if not chs:
                return 1
            spacing = max(0, len(chs) - 1)
            total = 0
            for c in chs:
                total += _curses_recursive_min_width(c)
            return max(1, total + spacing)
        elif cls == "YVBox":
            chs = list(getattr(widget, "_children", []) or [])
            if not chs:
                return 1
            widest = 1
            for c in chs:
                widest = max(widest, _curses_recursive_min_width(c))
            return max(1, widest)
        elif cls == "YAlignment":
            child = widget.child()
            return max(1, _curses_recursive_min_width(child))
        elif cls == "YReplacePoint":
            child = widget.child()
            return max(1, _curses_recursive_min_width(child))
        elif cls == "YFrame" or cls == "YCheckBoxFrame":
            child = widget.child()
            inner_min = _curses_recursive_min_width(child) if child is not None else 1
            return max(3, 2 + inner_min)  # borders(2) + inner
        else:
            return _leaf_min_width(widget)
    except Exception as e:
        try:
            _mod_logger.error("_curses_recursive_min_width error: %s", e, exc_info=True)
        except Exception:
            pass
        try:
            return max(1, int(getattr(widget, "_width", 10)))
        except Exception:
            return 10
