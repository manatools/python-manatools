#!/usr/bin/env python3

"""Headless check of YChartPie on the ncurses backend.

Draws the chart into a fake curses window (a character grid, so no terminal
is needed) and checks the rows: title, donut center text, label / value /
percent columns, bar lengths, scrolling with a "more" line, "No data", the
bars-only layout of YChartLegendPosition.Hidden; then drives _handle_key():
arrows, Home/End, Enter/Space, Enter with no selection, notify(False),
unfocused and disabled widgets.

Run directly: python3 test/test_chartpie_curses_headless.py (exit 0 = pass).
"""

import curses
import os
import sys

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from manatools.aui.yui_common import YChartLegendPosition, YEventReason  # noqa: E402
from manatools.aui.backends.curses.chartpiecurses import YChartPieCurses  # noqa: E402

FAILURES = []
POSTED = []
BLOCK = "█"


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


def make(label, slices, **kw):
    c = YChartPieCurses(None, label)
    c.findDialog = lambda: FakeDialog()
    c.setSlices(slices)
    for k, v in kw.items():
        getattr(c, k)(v)
    c._create_backend_widget()
    return c


def draw(c, width=50, height=8):
    win = FakeWindow(width, height)
    c._draw(win, 0, 0, width, height)
    return win


def main():
    c = make("Disk usage", [("System", 25), ("Home", 50), ("Free", 25)])
    win = draw(c)
    lines = win.lines()
    print("\n".join("     |" + line for line in lines))
    check("title row", lines[0] == "Disk usage" and win.attrs[0][0] & curses.A_BOLD)
    check("row: label value percent", "System" in lines[1] and "25" in lines[1] and "25.0%" in lines[1], lines[1])
    bars = [line.count(BLOCK) for line in lines[1:4]]
    check("bars proportional", bars[1] == 2 * bars[0] and bars[0] == bars[2] and bars[0] > 0, bars)
    check("height: header + 3", c._height == 4, c._height)

    c.setDonutRatio(0.5)
    c.setCenterText("100 GB")
    lines = draw(c).lines()
    check("donut: center text row", lines[1] == "100 GB", lines[1])

    c.setShowPercent(False)
    lines = draw(c).lines()
    check("percent hidden", "%" not in "".join(lines))

    c.setLegendPosition(YChartLegendPosition.Hidden)
    lines = draw(c).lines()
    check("legend hidden: bars only", "System" not in "".join(lines) and BLOCK in lines[2], lines)

    many = make("", [(f"slice {i}", 1) for i in range(20)])
    many._focused = True
    lines = draw(many, 40, 6).lines()
    check("scroll: more line", lines[5].startswith("…") and "↓15" in lines[5], lines[5])
    for _ in range(10):
        many._handle_key(curses.KEY_DOWN)
    lines = draw(many, 40, 6).lines()
    check("scroll: follows selection", any(line.startswith("■ slice 9 ") for line in lines)
          and many.selectedSlice() == 9, lines)
    many._handle_key(curses.KEY_END)
    lines = draw(many, 40, 6).lines()
    check("scroll: End shows last", "slice 19" in "".join(lines) and "↑" in lines[5], lines)

    narrow = make("", [("a very long slice label here", 3), ("b", 1)])
    lines = draw(narrow, 24, 3).lines()
    check("narrow: label elided, fits", "…" in lines[0] and all(len(line) <= 24 for line in lines), lines)

    empty = make("Empty", [])
    lines = draw(empty).lines()
    check("empty: No data", lines[1] == "No data", lines)
    zero = make("", [("a", 0), ("b", 0)])
    lines = draw(zero).lines()
    check("all zero: No data + rows, no bars", lines[0] == "No data" and "a" in lines[1]
          and BLOCK not in "".join(lines), lines)

    # -- keys ----------------------------------------------------------------
    k = make("", [("a", 1), ("b", 2), ("c", 3)])
    POSTED.clear()
    check("unfocused: keys ignored", not k._handle_key(curses.KEY_DOWN) and k.selectedSlice() == -1)
    k._focused = True
    check("Enter, no selection: not consumed", not k._handle_key(ord('\n')) and not POSTED)
    k._handle_key(curses.KEY_DOWN)
    check("Down selects first, no event", k.selectedSlice() == 0 and not POSTED)
    k._handle_key(curses.KEY_DOWN)
    k._handle_key(curses.KEY_DOWN)
    k._handle_key(curses.KEY_DOWN)
    check("Down stops at last", k.selectedSlice() == 2)
    k._handle_key(curses.KEY_HOME)
    check("Home", k.selectedSlice() == 0)
    check("Enter activates", k._handle_key(ord('\n')) and len(POSTED) == 1
          and POSTED[0].widget() is k and POSTED[0].reason() == YEventReason.Activated)
    k._handle_key(ord(' '))
    check("Space activates", len(POSTED) == 2)
    check("other keys not consumed", not k._handle_key(ord('x')))
    win = draw(k)
    check("focused row reversed", win.attrs[0][2] & curses.A_REVERSE)
    k.setNotify(False)
    k._handle_key(ord('\n'))
    check("notify off: no event", len(POSTED) == 2)
    k.setNotify(True)
    k.setEnabled(False)
    check("disabled: not focusable, keys ignored", not k._can_focus and not k._handle_key(ord('\n')))
    k.setEnabled(True)
    check("enabled again: focusable", k._can_focus)

    print("FAILED: " + ", ".join(FAILURES) if FAILURES else "all passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
