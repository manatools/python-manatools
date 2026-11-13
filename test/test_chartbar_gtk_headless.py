#!/usr/bin/env python3

"""Automated check of YChartBar on the GTK backend.

Needs a GDK display but no interaction; a headless one works:

    gtk4-broadwayd :5 &
    GDK_BACKEND=broadway BROADWAY_DISPLAY=:5 python3 test/test_chartbar_gtk_headless.py [out.png]

Paints sample charts (grouped/stacked, vertical/horizontal, negatives, value
labels, many categories, empty) into a cairo image surface, optionally saved
to PNG for a visual check; probes pixels (bar colors, negative bar below the
zero line); drives the input handlers (bar clicks in both orientations and
stacked mode, empty plot space, arrow keys, Enter, notify(False), tooltips);
shows one chart in a real Gtk.Window to make sure GTK draws and redraws it.

Exit code 0 = pass.
"""

import os
import sys
import time

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import gi  # noqa: E402
gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk, Gdk  # noqa: E402
import cairo  # noqa: E402

from manatools.aui.yui_common import YChartBarOrientation as O, YChartLegendPosition  # noqa: E402
from manatools.aui.backends.gtk.chartbargtk import YChartBarGtk  # noqa: E402

W, H = 460, 280
FAILURES = []
POSTED = []
WINDOWS = []
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
ROWS = [[30, 20, 5], [45, 25, -8], [28, 40, 12], [60, 15, -20], [52, 33, 7], [80, 10, 15]]
SERIES = ["CPU", "RAM", ("Swap", "#cc0000")]


class _Dialog:
    def _post_event(self, ev):
        POSTED.append(ev)


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
    if not cond:
        FAILURES.append(name)


def make(label="Load", cats=MONTHS, series=SERIES, rows=ROWS, orientation=O.Vertical,
         stacked=False, values=False, legend=YChartLegendPosition.Right, sel=None):
    c = YChartBarGtk(None, label)
    c.findDialog = lambda: _Dialog()
    c.setData(cats, series, rows)
    c.setOrientation(orientation)
    c.setStacked(stacked)
    c.setShowValues(values)
    c.setLegendPosition(legend)
    c._create_backend_widget()
    if sel:
        c.setSelectedBar(*sel)
    # Root the area so it gets the theme's style (text color) when painted.
    win = Gtk.Window()
    win.set_child(c.get_backend_widget())
    WINDOWS.append(win)
    paint(c, cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)))
    return c


def paint(c, cr):
    c.get_backend_widget().paint(cr, c, W, H)


def to_px(area, u, v):
    left, top, right, bottom, horizontal, vmin, span = area._plot
    if horizontal:
        return left + (v - vmin) / span * (right - left), top + u * (bottom - top)
    return left + u * (right - left), bottom - (v - vmin) / span * (bottom - top)


def centre(c, cat, ser):
    for cc, s, u0, u1, v0, v1, _col in c._bar_geometry():
        if (cc, s) == (cat, ser):
            return to_px(c.get_backend_widget(), (u0 + u1) / 2, (v0 + v1) / 2)
    raise KeyError((cat, ser))


def iterate(seconds=0.3):
    ctx = GLib.MainContext.default()
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        while ctx.pending():
            ctx.iteration(False)
        time.sleep(0.01)


def main():
    if not Gtk.init_check():
        print("SKIP: no GDK display (see the docstring for a headless one)")
        return 0

    cases = [
        dict(values=True, sel=(3, 0)),
        dict(stacked=True, values=True, legend=YChartLegendPosition.Bottom),
        dict(orientation=O.Horizontal, values=True, sel=(1, 2)),
        dict(orientation=O.Horizontal, stacked=True),
        dict(label="", cats=[f"Category {i}" for i in range(40)], series=["s"],
             rows=[[(i * 37) % 50 - 10] for i in range(40)]),
        dict(label="Empty", cats=[], series=[], rows=[]),
    ]
    sheet = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H * len(cases))
    cr = cairo.Context(sheet)
    cr.set_source_rgb(0.94, 0.94, 0.94)
    cr.paint()
    for i, kw in enumerate(cases):
        c = make(**kw)
        cr.save()
        cr.translate(0, H * i)
        paint(c, cr)
        cr.restore()
        cr.set_source_rgb(0.55, 0.55, 0.55)
        cr.rectangle(0, H * i, W, 1)
        cr.fill()
    if len(sys.argv) > 1:
        sheet.write_to_png(sys.argv[1])

    # -- pixel probes ----------------------------------------------------------
    c = make(label="", series=[("a", "#0000ff")], rows=[[r[0]] for r in ROWS[:3]] + [[-30]] + [[1]] * 2,
             legend=YChartLegendPosition.Hidden)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    paint(c, cairo.Context(surf))
    surf.flush()
    data, stride = surf.get_data(), surf.get_stride()

    def px(x, y):
        o = int(y) * stride + int(x) * 4
        return data[o + 2], data[o + 1], data[o], data[o + 3]
    x, y = centre(c, 1, 0)
    check("pixel: bar is series color", px(x, y)[:3] == (0, 0, 255), px(x, y))
    x, y = centre(c, 3, 0)
    zx, zy = to_px(c.get_backend_widget(), 0.6, 0)
    check("pixel: negative bar below zero line", y > zy and px(x, y)[:3] == (0, 0, 255), (y, zy, px(x, y)))
    x, _y = centre(c, 1, 0)
    _x, ty = to_px(c.get_backend_widget(), 0.25, 70)
    check("pixel: above bar is not bar color", px(x, ty)[:3] != (0, 0, 255), px(x, ty))

    # -- input -----------------------------------------------------------------
    c = make()
    area = c.get_backend_widget()
    POSTED.clear()
    area._on_pressed(None, 1, *centre(c, 2, 1))
    check("click: bar (Mar, RAM)", (c.selectedCategory(), c.selectedSeries()) == (2, 1) and len(POSTED) == 1,
          (c.selectedCategory(), c.selectedSeries(), len(POSTED)))
    area._on_pressed(None, 1, *centre(c, 3, 2))
    check("click: negative bar", (c.selectedCategory(), c.selectedSeries()) == (3, 2) and len(POSTED) == 2)
    area._on_pressed(None, 1, *to_px(area, 0.08, 75))
    check("click: empty plot space does nothing", len(POSTED) == 2)
    area._on_pressed(None, 1, 1, 1)
    check("click: outside plot does nothing", len(POSTED) == 2)
    check("key: Right consumed", area._on_key(None, Gdk.KEY_Right, 0, 0))
    check("key: Right moves category, no event", (c.selectedCategory(), c.selectedSeries()) == (4, 2)
          and len(POSTED) == 2)
    area._on_key(None, Gdk.KEY_Down, 0, 0)
    check("key: Down moves series", c.selectedSeries() == 1)
    check("key: Enter activates", area._on_key(None, Gdk.KEY_Return, 0, 0) and len(POSTED) == 3)
    check("key: other keys not consumed", not area._on_key(None, Gdk.KEY_a, 0, 0))
    c.setNotify(False)
    area._on_pressed(None, 1, *centre(c, 0, 0))
    check("notify off: selects, no event", (c.selectedCategory(), c.selectedSeries()) == (0, 0)
          and len(POSTED) == 3)
    c.setNotify(True)

    class _Tip:
        text = None

        def set_text(self, t):
            self.text = t
    tip = _Tip()
    c.setHelpText("help!")
    check("tooltip: bar text", area._on_query_tooltip(area, *centre(c, 1, 0), False, tip)
          and tip.text == "Feb · CPU: 45", tip.text)
    check("tooltip: help text elsewhere", area._on_query_tooltip(area, 1, 1, False, tip) and tip.text == "help!")

    c = make(orientation=O.Horizontal, stacked=True)
    area = c.get_backend_widget()
    POSTED.clear()
    area._on_pressed(None, 1, *centre(c, 5, 1))
    check("horizontal stacked: segment click", (c.selectedCategory(), c.selectedSeries()) == (5, 1)
          and len(POSTED) == 1, (c.selectedCategory(), c.selectedSeries()))
    area._on_key(None, Gdk.KEY_Up, 0, 0)
    check("horizontal: Up moves category", c.selectedCategory() == 4)
    area._on_key(None, Gdk.KEY_Right, 0, 0)
    check("horizontal: Right moves series", c.selectedSeries() == 2)

    c = make(cats=[f"c{i}" for i in range(2000)], rows=[[40 + (i * 37) % 30, 20 + i % 11, -5 - i % 7] for i in range(2000)], stacked=True, values=True)
    area = c.get_backend_widget()
    area._on_pressed(None, 1, *centre(c, 1000, 1))
    # 2000 categories in ~360 px: a pixel covers several bars, any of them is right
    check("dense: paints and hit-tests", abs(c.selectedCategory() - 1000) <= 6 and c.selectedSeries() == 1,
          (c.selectedCategory(), c.selectedSeries()))

    c = make(cats=[], series=[], rows=[])
    area = c.get_backend_widget()
    check("empty: keys not consumed", not area._on_key(None, Gdk.KEY_Right, 0, 0))
    check("empty: Enter not consumed", not area._on_key(None, Gdk.KEY_Return, 0, 0))

    # -- real window: GTK calls the draw func ----------------------------------
    c = make(label="Window", values=True)
    calls = []
    area = c.get_backend_widget()
    orig = area.paint
    area.paint = lambda *a: (calls.append(a[2:]), orig(*a))
    win = area.get_root()
    win.set_default_size(W, H)
    win.present()
    deadline = time.monotonic() + 3.0
    while not calls and time.monotonic() < deadline:
        iterate(0.1)
    check("window: draw func called", bool(calls), calls)
    check("window: natural size", area.get_content_width() >= 240 and area.get_content_height() > 0,
          (area.get_content_width(), area.get_content_height()))
    n = len(calls)
    c.setStacked(True)
    # Broadway without a connected browser throttles the frame clock.
    deadline = time.monotonic() + 3.0
    while len(calls) <= n and time.monotonic() < deadline:
        iterate(0.1)
    check("window: redraw on change", len(calls) > n)
    win.destroy()
    iterate(0.1)

    print("FAILED: " + ", ".join(FAILURES) if FAILURES else "all passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
