#!/usr/bin/env python3

"""Headless check of chart colors and glyphs on the ncurses backend.

No terminal needed: curses color functions are replaced by fakes.

- chart_color(): 256- and 88-color cubes, fixed distinct palette colors on
  16 and 8 colors (bright yellow via A_BOLD on 8), nearest hue for custom
  colors, never black, None without colors;
- chart_color_attr(): color pairs taken from the top of COLOR_PAIRS (the
  64-pair 8-color case included), shared per terminal color, no pair below
  the floor, fallback when the default background is not supported;
- chart_glyphs(): MUI_CURSES_ASCII override, DEC VT TERM entries, output
  encodings that cannot show the Unicode blocks;
- YChartPie / YChartBar drawn in ASCII mode emit ASCII only; a stacked bar
  chart without colors uses fill patterns in bars and legend.

Run directly: python3 test/test_chart_curses_colors_headless.py (exit 0 = pass).
"""

import curses
import os
import sys

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from manatools.aui.yui_common import YChartBase  # noqa: E402
from manatools.aui.backends.curses import commoncurses as cc  # noqa: E402
from manatools.aui.backends.curses.chartpiecurses import YChartPieCurses  # noqa: E402
from manatools.aui.backends.curses.chartbarcurses import YChartBarCurses  # noqa: E402

FAILURES = []
PALETTE = YChartBase.PALETTE


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
    if not cond:
        FAILURES.append(name)


class FakeCurses:
    """Patches the curses color API with a recording fake."""

    def __init__(self, colors, pairs, has=True, default_bg=True):
        self.colors, self.pairs, self.has, self.default_bg = colors, pairs, has, default_bg
        self.inits = []
        self.saved = {}

    def __enter__(self):
        for name in ("has_colors", "start_color", "use_default_colors", "init_pair", "color_pair"):
            self.saved[name] = getattr(curses, name)
        for name in ("COLORS", "COLOR_PAIRS"):
            self.saved[name] = getattr(curses, name, None)
        curses.has_colors = lambda: self.has
        curses.start_color = lambda: None
        curses.use_default_colors = lambda: None
        curses.init_pair = self._init_pair
        curses.color_pair = lambda pid: pid << 8
        curses.COLORS, curses.COLOR_PAIRS = self.colors, self.pairs
        cc._chart_pairs.clear()
        cc._chart_colors_ready = False
        return self

    def _init_pair(self, pid, fg, bg):
        if bg == -1 and not self.default_bg:
            raise curses.error("no default colors")
        if not 1 <= pid < self.pairs:
            raise curses.error("bad pair")
        self.inits.append((pid, fg, bg))

    def __exit__(self, *exc):
        for name, value in self.saved.items():
            if value is None:
                if hasattr(curses, name):
                    delattr(curses, name)
            else:
                setattr(curses, name, value)
        cc._chart_pairs.clear()
        cc._chart_colors_ready = False


class FakeWindow:
    def __init__(self, width, height, encoding="utf-8"):
        self.w, self.h, self.encoding = width, height, encoding
        self.grid = [[" "] * width for _ in range(height)]

    def addstr(self, y, x, text, attr=0):
        if not (0 <= y < self.h) or x < 0:
            raise curses.error("out of window")
        text.encode(self.encoding)          # what a real window would do
        for i, ch in enumerate(text):
            if x + i >= self.w:
                raise curses.error("past right edge")
            self.grid[y][x + i] = ch

    def text(self):
        return "\n".join("".join(r).rstrip() for r in self.grid)


def main():
    # -- chart_color --------------------------------------------------------
    check("no colors: None", cc.chart_color(PALETTE[0], 0) is None and cc.chart_color(PALETTE[0], 2) is None)
    eight = [cc.chart_color(c, 8) for c in PALETTE]
    check("8 colors: palette entries distinct", len(set(eight)) == 8, eight)
    check("8 colors: only the 8 basic colors", all(0 <= n <= 7 for n, _b in eight), eight)
    check("8 colors: yellow is bold yellow, orange plain yellow",
          eight[3] == (curses.COLOR_YELLOW, True) and eight[0] == (curses.COLOR_YELLOW, False), eight)
    sixteen = [cc.chart_color(c, 16) for c in PALETTE]
    check("16 colors: distinct numbers, no bold", len({n for n, _b in sixteen}) == 8
          and not any(b for _n, b in sixteen), sixteen)
    check("16 colors: bright yellow is 11", sixteen[3] == (11, False))
    for colors in (16, 88, 256):
        mapped = [cc.chart_color(c, colors) for c in PALETTE]
        check(f"{colors} colors: palette entries distinct", len(set(mapped)) == 8, mapped)
    check("88 colors: cube 16..79", all(16 <= cc.chart_color(c, 88)[0] <= 79 for c in PALETTE)
          and cc.chart_color("#ff0000", 88) == (16 + 48, False) and cc.chart_color("#000000", 88) == (16, False))
    check("256 colors: cube 16..231", all(16 <= cc.chart_color(c, 256)[0] <= 231 for c in PALETTE)
          and cc.chart_color("#ff0000", 256) == (196, False) and cc.chart_color("#ffffff", 256) == (231, False))
    check("direct color: exact RGB", cc.chart_color("#ff8000", 1 << 24) == (0xff8000, False)
          and cc.chart_color("#000000", 1 << 24) == (8, False))
    customs = ["#101010", "#800000", "#00ff00", "#0000aa", "#ffeeee", "#808080", "#ff00ff", "#00ffff"]
    for colors in (8, 16):
        mapped = [cc.chart_color(c, colors) for c in customs]
        check(f"{colors} colors: custom colors never black", all(n != curses.COLOR_BLACK for n, _b in mapped), mapped)
    check("custom: nearest xterm color on 16", [cc.chart_color(c, 16)[0] for c in customs]
          == [8, 1, 10, 4, 15, 8, 13, 14], [cc.chart_color(c, 16) for c in customs])
    check("custom: bright entries become bold on 8", cc.chart_color("#00ff00", 8) == (curses.COLOR_GREEN, True)
          and cc.chart_color("#0000aa", 8) == (curses.COLOR_BLUE, False)
          and cc.chart_color("#ffeeee", 8) == (curses.COLOR_WHITE, True))
    check("custom: near-black dark red is dark grey", cc.chart_color("#200000", 16) == (8, False))
    check("custom: dark grey is white on 8", cc.chart_color("#808080", 8) == (curses.COLOR_WHITE, False))

    # -- chart_color_attr ---------------------------------------------------
    with FakeCurses(8, 64) as fake:
        attrs = [cc.chart_color_attr(c) for c in PALETTE]
        check("8 colors / 64 pairs: every palette color gets a pair", all(a & ~curses.A_BOLD for a in attrs), attrs)
        check("pairs from the top of the range", sorted(p for p, _f, _b in fake.inits) == list(range(57, 64)),
              fake.inits)
        check("one pair per terminal color (orange and yellow share yellow)", len(fake.inits) == 7)
        check("bold only on bright yellow", [bool(a & curses.A_BOLD) for a in attrs]
              == [False, False, False, True, False, False, False, False])
        check("default background", all(b == -1 for _p, _f, b in fake.inits))
        check("cached: no new pairs", cc.chart_color_attr(PALETTE[0]) == attrs[0] and len(fake.inits) == 7)
    with FakeCurses(256, 65536) as fake:
        cc.chart_color_attr(PALETTE[0])
        check("256 colors: pair id capped to 32767", fake.inits[0][0] == 32767, fake.inits)
    with FakeCurses(8, 16) as fake:
        check("too few pairs: no color", cc.chart_color_attr(PALETTE[0]) == 0 and not fake.inits)
    with FakeCurses(8, 64, default_bg=False) as fake:
        a = cc.chart_color_attr(PALETTE[1])
        check("no default background: black background pair", a != 0 and fake.inits[0][2] == curses.COLOR_BLACK,
              fake.inits)
    with FakeCurses(0, 0, has=False):
        check("monochrome: attr 0", cc.chart_color_attr(PALETTE[0]) == 0)

    # -- chart_glyphs -------------------------------------------------------
    saved = {k: os.environ.get(k) for k in ("MUI_CURSES_ASCII", "TERM")}
    try:
        os.environ.pop("MUI_CURSES_ASCII", None)
        os.environ["TERM"] = "xterm-256color"
        check("utf-8 window: Unicode", not cc.chart_glyphs(FakeWindow(1, 1)).ascii)
        check("ascii window: ASCII", cc.chart_glyphs(FakeWindow(1, 1, "ascii")).ascii)
        check("latin-1 window: ASCII", cc.chart_glyphs(FakeWindow(1, 1, "latin-1")).ascii)
        for term in ("vt100", "vt52", "vt220", "vt102"):
            os.environ["TERM"] = term
            check(f"TERM={term}: ASCII", cc.chart_glyphs(FakeWindow(1, 1)).ascii)
        os.environ["MUI_CURSES_ASCII"] = "0"
        check("MUI_CURSES_ASCII=0 forces Unicode", not cc.chart_glyphs(FakeWindow(1, 1)).ascii)
        os.environ["TERM"] = "xterm"
        os.environ["MUI_CURSES_ASCII"] = "1"
        check("MUI_CURSES_ASCII=1 forces ASCII", cc.chart_glyphs(FakeWindow(1, 1)).ascii)
        g = cc.chart_glyphs()
        check("ASCII glyphs are ASCII", g.all().isascii() and len(set(g.patterns)) == 4)
        hints = [YChartPieCurses(None).key_hints(), YChartBarCurses(None).key_hints()]
        stacked = YChartBarCurses(None)
        stacked.setStacked(True)
        hints.append(stacked.key_hints())
        check("ASCII key hints", all(h.isascii() for h in hints) and "Arrows" in hints[2], hints)

        # -- charts in ASCII mode, no colors ------------------------------
        pie = YChartPieCurses(None, "Disk")
        pie.setSlices([("System with a long name", 30), ("Home", 50), ("Free", 20)])
        win = FakeWindow(30, 4, "ascii")
        pie._draw(win, 0, 0, 30, 4)
        check("pie ASCII: drawn, ASCII only", "#" in win.text() and win.text().isascii(), win.text())
        check("pie ASCII: cut label uses ~", "~" in win.text(), win.text())

        bar = YChartBarCurses(None, "Load")
        bar.setData(["Jan", "Feb"], ["CPU", "RAM"], [[30, 20], [-10, 25]])
        bar.setStacked(True)
        win = FakeWindow(40, 6, "ascii")
        bar._draw(win, 0, 0, 40, 6)
        text = win.text()
        print("\n".join("     |" + line for line in text.splitlines()))
        check("bar ASCII: ASCII only", text.isascii(), text)
        lines = text.splitlines()
        check("bar ASCII: legend shows the patterns", lines[1].startswith("# CPU") and "= RAM" in lines[1], lines[1])
        check("bar ASCII: stacked segments patterned", "#" in lines[2] and "=" in lines[2], lines[2])
        check("bar ASCII: zero column |", "|" in lines[3], lines[3])
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    print("FAILED: " + ", ".join(FAILURES) if FAILURES else "all passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
