#!/usr/bin/env python3

"""Headless check of YChartGauge on the ncurses backend.

Draws the gauge into a fake curses window (a character grid, so no terminal
is needed) and checks the rows: title, value + subtitle, band strip, value
bar (fill origin, clamping, target marker), tick labels, legend, hidden
parts and the row count; monochrome patterns versus colors (with a stubbed
color function), ASCII glyphs, control characters; then drives
_handle_key(): Enter/Space, notify(False), unfocused and disabled widgets.

Run directly: python3 test/test_chartgauge_curses_headless.py (exit 0 = pass).
"""

import curses
import os
import sys

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ["MUI_CURSES_ASCII"] = "0"     # these checks expect the Unicode glyphs

from manatools.aui.yui_common import YChartLegendPosition, YEventReason, YUIDimension  # noqa: E402
from manatools.aui.backends.curses import chartgaugecurses  # noqa: E402
from manatools.aui.backends.curses.chartgaugecurses import YChartGaugeCurses  # noqa: E402

FAILURES = []
POSTED = []
BLOCK, TRACK, STRIP, ZERO = "█", "░", "▀", "│"
BANDS = [(0, 60, None, "OK"), (60, 85, None, "Warn"), (85, 100, None, "Crit")]


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
    if not cond:
        FAILURES.append(name)


class FakeWindow:
    """Records addstr() calls on a character grid."""

    def __init__(self, width, height):
        self.w, self.h = width, height
        self.grid = [[" "] * width for _ in range(height)]
        self.attrs = [[0] * width for _ in range(height)]

    def addstr(self, y, x, text, attr=0):
        if not (0 <= y < self.h) or x < 0:
            raise curses.error("out of window")
        for i, ch in enumerate(text):
            if x + i >= self.w:
                raise curses.error("past right edge")
            self.grid[y][x + i] = ch
            self.attrs[y][x + i] = attr

    def lines(self):
        return ["".join(r).rstrip() for r in self.grid]


class FakeDialog:
    def _post_event(self, ev):
        POSTED.append(ev)

    def mark_dirty(self):
        pass


def make(label="CPU", value=72, bands=BANDS, **kw):
    g = YChartGaugeCurses(None, label)
    g.findDialog = lambda: FakeDialog()
    g.setBands(bands)
    g.setValue(value)
    for k, v in kw.items():
        getattr(g, k)(v)
    g._create_backend_widget()
    return g


def draw(g, width=40, height=8):
    win = FakeWindow(width, height)
    g._draw(win, 0, 0, width, height)
    return win


def main():
    g = make(setUnit="%", setSubtitle="load", setTarget=90)
    win = draw(g)
    lines = win.lines()
    print("\n".join("     |" + line for line in lines))
    check("rows: title value strip bar ticks legend", g._height == 6, g._height)
    check("not stretchable vertically", not g.stretchable(YUIDimension.YD_VERT)
          and g.stretchable(YUIDimension.YD_HORIZ))
    check("title bold", lines[0] == "CPU" and win.attrs[0][0] & curses.A_BOLD)
    check("value + subtitle", lines[1] == "72% load" and win.attrs[1][0] & curses.A_BOLD
          and win.attrs[1][4] & curses.A_DIM, lines[1])
    bar = lines[3]
    check("bar: 72% filled", bar.count(BLOCK) == round(0.72 * 40) and bar.startswith(BLOCK), bar)
    check("bar: track after value", bar[30] == TRACK, bar)
    check("bar: target marker at 90", bar[36] == ZERO and win.attrs[3][36] & curses.A_BOLD, bar)
    check("ticks: ends", lines[4].startswith("0 ") and lines[4].endswith("100"), lines[4])
    check("ticks: inner at columns", lines[4][15:17] == "40", lines[4])
    check("mono strip: shaded patterns, not the solid block", BLOCK not in lines[2]
          and lines[2][0] == "▓" and lines[2][30] == "▒" and lines[2][39] == "░", lines[2])
    check("legend: labelled bands", lines[5].startswith("▓ OK 0..60  ▒ Warn 60..85"), lines[5])

    # -- fill origin, clamping ---------------------------------------------------
    g.setRange(-50, 50)
    g.setValue(-20)
    bar = draw(g).lines()[3]
    check("zero-spanning: fills from the middle", bar[:12] == TRACK * 12 and bar[12:20] == BLOCK * 8
          and bar[20] == TRACK, bar)
    check("target outside range: no marker", ZERO not in bar)
    g.setRange(0, 100)
    g.setValue(500)
    lines = draw(g).lines()
    check("above range: full bar, real value text", lines[3].count(BLOCK) == 40 - 1 and lines[1].startswith("500%"),
          lines[:4])
    check("target on fill: reversed", draw(g).attrs[3][36] & curses.A_REVERSE)
    g.setValue(0.1)
    check("tiny value: one cell", draw(g).lines()[3].count(BLOCK) == 1)
    g.setValue(0)
    check("zero value: empty bar", draw(g).lines()[3].count(BLOCK) == 0)

    # -- colors (stubbed) ------------------------------------------------------
    real = chartgaugecurses.chart_color_attr
    chartgaugecurses.chart_color_attr = lambda hexc: {"#009e73": 1 << 8, "#e69f00": 2 << 8,
                                                      "#d55e00": 3 << 8}.get(hexc, 4 << 8)
    try:
        g.setValue(72)
        win = draw(g)
        lines = win.lines()
        check("color strip: strip glyph in band colors", lines[2] == STRIP * 40
              and win.attrs[2][0] == 1 << 8 and win.attrs[2][30] == 2 << 8 and win.attrs[2][39] == 3 << 8,
              (lines[2], win.attrs[2][0], win.attrs[2][30]))
        check("color bar: band color of the value", win.attrs[3][0] == 2 << 8)
        check("color legend: swatches", lines[5].startswith("■ OK") and win.attrs[5][0] == 1 << 8, lines[5])
    finally:
        chartgaugecurses.chart_color_attr = real

    # -- hidden parts ------------------------------------------------------------
    h = make(label="", bands=[], setShowTicks=False, setShowValue=False)
    lines = draw(h).lines()
    check("minimal: bar only", h._height == 1 and lines[0].count(TRACK) == 11 and lines[0].count(BLOCK) == 29,
          (h._height, lines[0]))
    h.setLegendPosition(YChartLegendPosition.Hidden)
    g.setLegendPosition(YChartLegendPosition.Hidden)
    check("legend hidden: one row less", g._height == 5, g._height)

    # -- ASCII and narrow --------------------------------------------------------
    os.environ["MUI_CURSES_ASCII"] = "1"
    lines = draw(g).lines()
    os.environ["MUI_CURSES_ASCII"] = "0"
    check("ascii glyphs", lines[3].startswith("#") and "-" in lines[3] and "|" in lines[3]
          and all(ord(ch) < 128 for line in lines for ch in line), lines)
    lines = draw(g, 12, 8).lines()
    check("narrow: fits", all(len(line) <= 12 for line in lines) and lines[4].startswith("0")
          and lines[4].endswith("100"), lines)

    ctl = make("t\nx", setSubtitle="a\tb\x1b[2J")
    lines = draw(ctl).lines()
    check("control characters replaced", lines[0] == "t?x" and lines[1] == "72 a?b?[2J", lines[:2])

    # -- keys ----------------------------------------------------------------
    k = make()
    POSTED.clear()
    check("unfocused: keys ignored", not k._handle_key(ord('\n')) and not POSTED)
    k._focused = True
    check("Enter activates", k._handle_key(ord('\n')) and len(POSTED) == 1
          and POSTED[0].widget() is k and POSTED[0].reason() == YEventReason.Activated)
    check("Space activates", k._handle_key(ord(' ')) and len(POSTED) == 2)
    check("other keys not consumed", not k._handle_key(curses.KEY_DOWN))
    win = draw(k)
    check("focus shown on value row", win.attrs[1][0] & curses.A_REVERSE)
    k.setNotify(False)
    k._handle_key(ord('\n'))
    check("notify off: no event", len(POSTED) == 2)
    k.setNotify(True)
    k.setEnabled(False)
    check("disabled: not focusable, keys ignored", not k._can_focus and not k._handle_key(ord('\n')))
    k.setEnabled(True)
    check("enabled again: focusable", k._can_focus)
    check("key hints", k.key_hints() == "ENTER=Activate")

    print("FAILED: " + ", ".join(FAILURES) if FAILURES else "all passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
