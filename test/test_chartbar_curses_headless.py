#!/usr/bin/env python3

"""Headless check of YChartBar on the ncurses backend.

Draws the chart into a fake curses window (a character grid, so no terminal
is needed) and checks: title and series legend rows, grouped rows (category
on the first row of its group, series column), proportional bar lengths,
negative bars left of the zero column, the axis row, stacked segments
(patterns without colors), value column (stacked: totals), scrolling with a
"more" line, narrow widths, "No data"; then drives _handle_key(): Up/Down,
Home/End, Left/Right in stacked mode, Enter/Space, Enter with no selection,
notify(False), unfocused and disabled widgets.

Run directly: python3 test/test_chartbar_curses_headless.py (exit 0 = pass).
"""

import curses
import os
import sys

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ["MUI_CURSES_ASCII"] = "0"     # these checks expect the Unicode glyphs

from manatools.aui.yui_common import YChartLegendPosition, YEventReason  # noqa: E402
from manatools.aui.backends.curses.chartbarcurses import YChartBarCurses  # noqa: E402

FAILURES = []
POSTED = []
BLOCK, ZERO = "█", "│"


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


def make(label="Load", cats=("Jan", "Feb"), series=("CPU", "RAM"), rows=((40, 20), (10, -10)), **kw):
    c = YChartBarCurses(None, label)
    c.findDialog = lambda: FakeDialog()
    c.setData(list(cats), list(series), [list(r) for r in rows])
    for k, v in kw.items():
        getattr(c, k)(v)
    c._create_backend_widget()
    return c


def draw(c, width=50, height=10):
    win = FakeWindow(width, height)
    c._draw(win, 0, 0, width, height)
    return win


def main():
    c = make()
    win = draw(c)
    lines = win.lines()
    print("\n".join("     |" + line for line in lines))
    check("title row", lines[0] == "Load" and win.attrs[0][0] & curses.A_BOLD)
    check("legend row", "CPU" in lines[1] and "RAM" in lines[1] and lines[1].startswith("■"))
    check("grouped: category on first row only", lines[2].startswith("Jan CPU") and lines[3].startswith("    RAM"))
    b = [line.count(BLOCK) for line in lines[2:6]]
    check("bars proportional", abs(b[0] - 2 * b[1]) <= 1 and abs(b[2] - b[3]) <= 1 and b[0] > b[2] > 0, b)
    zcol = lines[2].index(ZERO)
    check("zero column on every bar row", all(line[zcol] == ZERO for line in lines[2:6]), lines[2:6])
    check("negative bar left of zero", lines[5].rstrip().endswith(ZERO) and BLOCK in lines[5][:zcol], lines[5])
    check("positive bar right of zero", BLOCK in lines[2][zcol + 1:] and BLOCK not in lines[2][:zcol])
    check("axis row", lines[6].split() == ["-10", "0", "40"], lines[6])
    check("height: header + 3 + axis", c._height == 6, c._height)

    c.setShowValues(True)
    lines = draw(c).lines()
    check("value column", lines[2].endswith("40") and lines[5].endswith("-10"), lines[2:6])

    c.setLegendPosition(YChartLegendPosition.Hidden)
    lines = draw(c).lines()
    check("legend hidden", lines[1].startswith("Jan"), lines[1])

    s = make(series=("CPU", "RAM", "Swap"), rows=((30, 20, 5), (45, 25, -8)), setStacked=True, setShowValues=True)
    lines = draw(s, 50, 8).lines()
    print("\n".join("     |" + line for line in lines))
    check("stacked: one row per category", lines[2].startswith("Jan") and lines[3].startswith("Feb")
          and "CPU" not in lines[2], lines[2:4])
    check("stacked: patterns without colors", "▓" in lines[2] and "▒" in lines[2])
    check("stacked: totals", lines[2].endswith("55") and lines[3].endswith("62"), lines[2:4])
    check("stacked: negative segment left of zero", lines[3].index("▒") < lines[3].index(ZERO), lines[3])

    single = make(series=("",), rows=((1,), (3,)))
    lines = draw(single).lines()
    check("single unnamed series: no legend, no series column",
          lines[1].startswith("Jan ") and lines[1][4:].lstrip().startswith(BLOCK)
          and "\u25a0" not in "".join(lines), lines[:3])

    many = make(label="", cats=[f"c{i}" for i in range(20)], series=("x",),
                rows=[(i + 1,) for i in range(20)], setLegendPosition=YChartLegendPosition.Hidden)
    many._focused = True
    lines = draw(many, 40, 6).lines()
    check("scroll: more line", lines[4].startswith("…") and "↓16" in lines[4], lines)
    for _ in range(10):
        many._handle_key(curses.KEY_DOWN)
    lines = draw(many, 40, 6).lines()
    check("scroll: follows selection", any(line.startswith("c9 ") for line in lines)
          and many.selectedCategory() == 9, lines)
    many._handle_key(curses.KEY_END)
    lines = draw(many, 40, 6).lines()
    check("scroll: End shows last", any(line.startswith("c19") for line in lines) and "↑" in lines[4], lines)

    narrow = make(cats=("a very long category label",), series=("s",), rows=((5,),))
    lines = draw(narrow, 24, 4).lines()
    check("narrow: label cut, fits", "…" in lines[2] and all(len(line) <= 24 for line in lines), lines)

    empty = make(cats=(), series=(), rows=())
    lines = draw(empty).lines()
    check("empty: No data", lines[1] == "No data", lines)

    # -- keys ----------------------------------------------------------------
    k = make()
    POSTED.clear()
    check("unfocused: keys ignored", not k._handle_key(curses.KEY_DOWN) and k.selectedCategory() == -1)
    k._focused = True
    check("Enter, no selection: not consumed", not k._handle_key(ord('\n')) and not POSTED)
    k._handle_key(curses.KEY_DOWN)
    check("Down selects first, no event", (k.selectedCategory(), k.selectedSeries()) == (0, 0) and not POSTED)
    k._handle_key(curses.KEY_DOWN)
    k._handle_key(curses.KEY_DOWN)
    check("Down walks series then categories", (k.selectedCategory(), k.selectedSeries()) == (1, 0))
    k._handle_key(curses.KEY_END)
    check("End", (k.selectedCategory(), k.selectedSeries()) == (1, 1))
    check("Left/Right not consumed when grouped", not k._handle_key(curses.KEY_LEFT))
    check("Enter activates", k._handle_key(ord('\n')) and len(POSTED) == 1
          and POSTED[0].widget() is k and POSTED[0].reason() == YEventReason.Activated)
    k._handle_key(ord(' '))
    check("Space activates", len(POSTED) == 2)
    win = draw(k)
    check("focused row reversed", win.attrs[5][0] & curses.A_REVERSE, [r[:3] for r in win.attrs])
    k.setNotify(False)
    k._handle_key(ord('\n'))
    check("notify off: no event", len(POSTED) == 2)
    k.setNotify(True)
    k.setStacked(True)
    k._handle_key(curses.KEY_HOME)
    check("stacked: Home keeps series", (k.selectedCategory(), k.selectedSeries()) == (0, 1))
    k._handle_key(curses.KEY_LEFT)
    check("stacked: Left moves segment", k.selectedSeries() == 0)
    k._handle_key(curses.KEY_DOWN)
    check("stacked: Down moves category", k.selectedCategory() == 1)
    k.setEnabled(False)
    check("disabled: not focusable, keys ignored", not k._can_focus and not k._handle_key(ord('\n')))
    k.setEnabled(True)
    check("enabled again: focusable", k._can_focus)
    check("key hints follow mode", "←" in k.key_hints())

    print("FAILED: " + ", ".join(FAILURES) if FAILURES else "all passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
