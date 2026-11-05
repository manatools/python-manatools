# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Common helpers for the curses backend.

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.curses

Also provides mnemonic extraction from labels that may use Qt ('&X' / '&&')
or GTK ('_X' / '__') style markers.
'''

import curses
import curses.ascii
import locale
import sys
import os
import re
import time
import logging
from typing import Tuple, Optional
from ...yui_common import *

def extract_mnemonic(label: Optional[str]) -> Tuple[Optional[str], str]:
    """Extract mnemonic character and return (mnemonic_char, clean_label).

    - Supports Qt-style '&' mnemonic: '&F' => mnemonic 'f'. '&&' => literal '&'.
    - Supports GTK-style '_' mnemonic: '_F' => mnemonic 'f'. '__' => literal '_'.
    - If no mnemonic found, returns (None, original_label).

    The returned clean_label has mnemonic markers removed/unescaped.
    """
    if label is None:
        return None, label
    s = str(label)
    if not s:
        return None, s

    # Prefer Qt-style '&' parsing first
    mn: Optional[str] = None
    out = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == '&':
            # literal '&&'
            if i + 1 < n and s[i + 1] == '&':
                out.append('&')
                i += 2
                continue
            # mnemonic (single '&')
            if i + 1 < n and mn is None:
                mn = s[i + 1].lower()
                # do not add '&' to output; just skip marker and continue
                i += 1
                continue
            # stray '&' at end -> drop
            i += 1
            continue
        out.append(ch)
        i += 1

    # If no '&' mnemonic found, try '_' GTK style
    if mn is None and '_' in s:
        out2 = []
        i = 0
        n = len(s)
        while i < n:
            ch = s[i]
            if ch == '_':
                if i + 1 < n and s[i + 1] == '_':
                    out2.append('_')
                    i += 2
                    continue
                if i + 1 < n and mn is None:
                    mn = s[i + 1].lower()
                    i += 1
                    continue
                i += 1
                continue
            out2.append(ch)
            i += 1
        return mn, ''.join(out2)

    return mn, ''.join(out)


def split_mnemonic(label: Optional[str]) -> Tuple[Optional[str], Optional[int], str]:
    """Return (mnemonic_char, mnemonic_index_in_clean, clean_label).

    Works like extract_mnemonic but also returns the index in the cleaned
    label where the mnemonic applies, or None if not present.
    """
    if label is None:
        return None, None, label
    s = str(label)
    if not s:
        return None, None, s

    mn = None
    idx = None
    out = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == '&':
            if i + 1 < n and s[i + 1] == '&':
                out.append('&')
                i += 2
                continue
            if i + 1 < n and mn is None:
                mn = s[i + 1].lower()
                idx = len(out)
                i += 1
                continue
            i += 1
            continue
        out.append(ch)
        i += 1
    if mn is None and '_' in s:
        out2 = []
        i = 0
        n = len(s)
        while i < n:
            ch = s[i]
            if ch == '_':
                if i + 1 < n and s[i + 1] == '_':
                    out2.append('_')
                    i += 2
                    continue
                if i + 1 < n and mn is None:
                    mn = s[i + 1].lower()
                    idx = len(out2)
                    i += 1
                    continue
                i += 1
                continue
            out2.append(ch)
            i += 1
        return mn, idx, ''.join(out2)
    return mn, idx, ''.join(out)
 

__all__ = ["pixels_to_chars", "_curses_recursive_min_height", "_curses_recursive_min_width",
           "_curses_help_text_changed"]

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
        elif cls == "YPaned":
            chs = [c for c in list(getattr(widget, "_children", []) or []) if c is not None and c.visible()]
            if not chs:
                return 1
            orient = getattr(widget, "_orientation", YUIDimension.YD_HORIZ)
            if orient == YUIDimension.YD_VERT:
                return max(1, sum(_curses_recursive_min_height(c) for c in chs))
            return max(1, max(_curses_recursive_min_height(c) for c in chs))
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


def _curses_help_text_changed(widget):
    """Reflect a setHelpText() call on screen.

    Help text is shown on demand: F1 opens an overlay with the focused
    widget's helpText(), and the footer advertises F1 only when there is
    something to show.  Update an overlay already open for *widget* and ask
    its dialog to redraw so the footer hint follows the new text.
    """
    try:
        dialog = widget.findDialog()
        if dialog is None:
            return
        if getattr(dialog, "_focused_widget", None) is widget and \
                getattr(dialog, "_help_overlay_text", None) is not None:
            text = widget.helpText()
            if text:
                dialog._help_overlay_text = str(text)
            else:
                dialog._help_overlay_text = None
                dialog._help_overlay_until = 0.0
                dialog._help_overlay_pos = None
        dialog._needs_redraw = True
    except Exception:
        _mod_logger.debug("_curses_help_text_changed failed", exc_info=True)


# ---------------------------------------------------------------------------
# Chart colors and glyphs (YChartPie / YChartBar)
# ---------------------------------------------------------------------------
#
# Colors depend on what the terminal reports (curses.COLORS):
#   2**24   direct color (xterm-direct): the exact RGB value;
#   >= 256  xterm 6x6x6 color cube (16..231), nearest level per channel;
#   >= 88   xterm-88color 4x4x4 cube (16..79), fixed distinct entries for
#           the chart palette;
#   >= 16   the 16 ANSI colors: fixed distinct colors for the chart palette,
#           nearest xterm ANSI color (RGB distance) for custom ones;
#   >= 8    the 8 ANSI colors: same, bright variants approximated with A_BOLD;
#   else    no color (monochrome, e.g. vt100): charts rely on labels, fill
#           patterns and bold/reverse.
# Black is never used as a foreground (invisible on dark backgrounds).

# Fixed 8/16-color choice for YChartBase.PALETTE, same order:
# (8-color number, A_BOLD on 8 colors, 16-color number)
_CHART_BASIC = (
    (curses.COLOR_YELLOW, False, 3),     # orange          -> yellow
    (curses.COLOR_CYAN, False, 14),      # sky blue        -> (bright) cyan
    (curses.COLOR_GREEN, False, 2),      # bluish green    -> green
    (curses.COLOR_YELLOW, True, 11),     # yellow          -> bright yellow
    (curses.COLOR_BLUE, False, 4),       # blue            -> blue
    (curses.COLOR_RED, False, 1),        # vermillion      -> red
    (curses.COLOR_MAGENTA, False, 5),    # reddish purple  -> magenta
    (curses.COLOR_WHITE, False, 7),      # grey            -> white (light grey)
)
_CHART_BASIC_BY_HEX = dict(zip(YChartBase.PALETTE, _CHART_BASIC))
# The 88-color cube is coarse (orange and vermillion would collide): fixed
# cube entries for the palette, same order.
_CHART_88 = (68, 43, 21, 72, 22, 48, 53, 37)
_CHART_88_BY_HEX = dict(zip(YChartBase.PALETTE, _CHART_88))
# xterm's default 16 ANSI colors (RGB), used to map custom colors on 8/16.
_XTERM_16 = (
    (0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0),
    (0, 0, 238), (205, 0, 205), (0, 205, 205), (229, 229, 229),
    (127, 127, 127), (255, 0, 0), (0, 255, 0), (255, 255, 0),
    (92, 92, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255),
)
_CUBE_88 = (0, 139, 205, 255)
_CUBE_256 = (0, 95, 135, 175, 215, 255)

# terminal color number -> color pair id, shared by every chart.  Pairs are
# taken from the top of the range so the low ids other widgets use stay free.
_chart_pairs = {}
_CHART_PAIR_FLOOR = 32
_chart_colors_ready = False


def _nearest_level(levels, value):
    return min(range(len(levels)), key=lambda i: abs(levels[i] - value))


def chart_color(hex_color: str, colors: int):
    """Terminal color for *hex_color* on a terminal with *colors* colors.

    Returns ``(color_number, bold)`` or None when the terminal has no
    usable colors.  ``bold`` is only set on 8-color terminals, to get the
    bright variant.
    """
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    if colors >= 1 << 24:
        # Direct-color terminals (e.g. xterm-direct): numbers 0-7 are the ANSI
        # colors, every other number is a 24-bit RGB value.
        return max(8, (r << 16) | (g << 8) | b), False
    if colors >= 256:
        q = [_nearest_level(_CUBE_256, v) for v in (r, g, b)]
        return 16 + 36 * q[0] + 6 * q[1] + q[2], False
    if colors >= 88:
        if hex_color.lower() in _CHART_88_BY_HEX:
            return _CHART_88_BY_HEX[hex_color.lower()], False
        q = [_nearest_level(_CUBE_88, v) for v in (r, g, b)]
        return 16 + 16 * q[0] + 4 * q[1] + q[2], False
    if colors < 8:
        return None
    fixed = _CHART_BASIC_BY_HEX.get(hex_color.lower())
    if fixed is not None:
        return (fixed[2], False) if colors >= 16 else (fixed[0], fixed[1])
    # Custom colors: nearest entry of the standard xterm 16-color palette,
    # black excluded.  On 8 colors a bright entry becomes base color + A_BOLD
    # (bright black, i.e. dark grey, becomes white).
    # Greys (low chroma) only map to the grey entries, so a near-black does
    # not turn red.
    candidates = (8, 7, 15) if max(r, g, b) - min(r, g, b) < 40 else range(1, 16)
    best = min(candidates, key=lambda i: sum((a - c) ** 2 for a, c in zip(_XTERM_16[i], (r, g, b))))
    if colors >= 16:
        return best, False
    if best == 8:
        return curses.COLOR_WHITE, False
    return (best - 8, True) if best > 8 else (best, False)


def chart_color_attr(hex_color: str) -> int:
    """curses attribute drawing *hex_color* as foreground; 0 without colors
    (or when the terminal runs out of color pairs)."""
    global _chart_colors_ready
    try:
        if not curses.has_colors():
            return 0
        mapped = chart_color(hex_color, int(getattr(curses, "COLORS", 0)))
        if mapped is None:
            return 0
        number, bold = mapped
        extra = curses.A_BOLD if bold else 0
        pid = _chart_pairs.get(number)
        if pid is None:
            top = min(int(getattr(curses, "COLOR_PAIRS", 0)), 32768) - 1
            pid = top - len(_chart_pairs)
            if pid < _CHART_PAIR_FLOOR:
                return extra
            if not _chart_colors_ready:
                try:
                    curses.start_color()
                    curses.use_default_colors()
                except Exception:
                    pass
                _chart_colors_ready = True
            try:
                curses.init_pair(pid, number, -1)           # default background
            except Exception:
                curses.init_pair(pid, number, curses.COLOR_BLACK)
            _chart_pairs[number] = pid
        return curses.color_pair(pid) | extra
    except Exception:
        return 0


class _ChartGlyphs:
    def __init__(self, ascii_only: bool):
        self.ascii = ascii_only
        if ascii_only:
            self.block, self.swatch, self.zero = "#", "#", "|"
            self.patterns = ("#", "=", "+", ":")
            self.ellipsis, self.up, self.down = "~", "^", "v"
        else:
            self.block, self.swatch, self.zero = "\u2588", "\u25a0", "\u2502"
            self.patterns = ("\u2588", "\u2593", "\u2592", "\u2591")
            self.ellipsis, self.up, self.down = "\u2026", "\u2191", "\u2193"

    def all(self) -> str:
        return (self.block + self.swatch + self.zero + "".join(self.patterns)
                + self.ellipsis + self.up + self.down)


_CHART_UNICODE = _ChartGlyphs(False)
_CHART_ASCII = _ChartGlyphs(True)
# DEC hardware terminals (and their terminfo entries) have no Unicode.
_ASCII_TERMS = re.compile(r"^vt\d")


def chart_glyphs(window=None) -> _ChartGlyphs:
    """Glyph set for charts: Unicode blocks, or ASCII on terminals that
    cannot show them.

    ASCII is used when MUI_CURSES_ASCII is 1/yes/true, when TERM is a DEC VT
    entry (vt52, vt100, vt220, ...) or when the output encoding cannot
    encode the Unicode glyphs; MUI_CURSES_ASCII=0/no/false forces Unicode.
    """
    force = os.environ.get("MUI_CURSES_ASCII", "").strip().lower()
    if force in ("1", "yes", "true", "on"):
        return _CHART_ASCII
    if force in ("0", "no", "false", "off"):
        return _CHART_UNICODE
    if _ASCII_TERMS.match(os.environ.get("TERM", "")):
        return _CHART_ASCII
    encoding = getattr(window, "encoding", None) or locale.getpreferredencoding(False) or "ascii"
    try:
        _CHART_UNICODE.all().encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return _CHART_ASCII
    return _CHART_UNICODE

