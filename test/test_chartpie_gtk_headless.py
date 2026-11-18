#!/usr/bin/env python3

"""Automated check of YChartPie on the GTK backend.

Needs a GDK display but no interaction; a headless one works:

    gtk4-broadwayd :5 &
    GDK_BACKEND=broadway BROADWAY_DISPLAY=:5 python3 test/test_chartpie_gtk_headless.py [out.png]

Paints sample charts (pie, donut, single slice, empty, 30 slices) into a
cairo image surface, optionally saved to PNG for a visual check, shows one
chart in a real Gtk.Window to make sure GTK draws it, and drives the input
handlers: slice and legend-row clicks, outside and donut-hole clicks,
arrow/Enter keys, notify(False), query-tooltip.

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

from manatools.aui.yui_common import YChartLegendPosition  # noqa: E402
from manatools.aui.backends.gtk.chartpiegtk import YChartPieGtk  # noqa: E402

W, H = 420, 260
FAILURES = []
POSTED = []
WINDOWS = []


class _Dialog:
    def _post_event(self, ev):
        POSTED.append(ev)


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
    if not cond:
        FAILURES.append(name)


def make(label, slices, ratio=0.0, pos=YChartLegendPosition.Right, center="", sel=-1):
    c = YChartPieGtk(None, label)
    c.findDialog = lambda: _Dialog()
    c.setSlices(slices)
    c.setDonutRatio(ratio)
    c.setLegendPosition(pos)
    c.setCenterText(center)
    c._create_backend_widget()
    if sel >= 0:
        c.setSelectedSlice(sel)
    # Root the area so it gets the theme's style (text color) when painted.
    win = Gtk.Window()
    win.set_child(c.get_backend_widget())
    WINDOWS.append(win)
    return c


def paint(c, cr):
    c.get_backend_widget().paint(cr, c, W, H)


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
        ("Disk usage", [("System", 30), ("Home & stuff", 10, "#ff0000"), ("Free", 60)],
         0, YChartLegendPosition.Right, "", 1),
        ("Donut", [("a", 30), ("b", 10), ("c", 5), ("d", 55)], 0.55, YChartLegendPosition.Bottom, "100 GB", 3),
        ("", [("one", 1)], 0, YChartLegendPosition.Hidden, "", -1),
        ("Empty", [], 0, YChartLegendPosition.Right, "", -1),
        ("Many", [(f"slice number {i}", i + 1) for i in range(30)], 0.3, YChartLegendPosition.Right, "", 5),
    ]
    sheet = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H * len(cases))
    cr = cairo.Context(sheet)
    cr.set_source_rgb(0.94, 0.94, 0.94)
    cr.paint()
    for i, args in enumerate(cases):
        c = make(*args)
        cr.save()
        cr.translate(0, H * i)
        paint(c, cr)
        cr.restore()
        cr.set_source_rgb(0.55, 0.55, 0.55)
        cr.rectangle(0, H * i, W, 1)
        cr.fill()
    check("paint: no cairo error", sheet.status() == cairo.STATUS_SUCCESS if hasattr(sheet, "status") else True)
    if len(sys.argv) > 1:
        sheet.write_to_png(sys.argv[1])

    # Pixel probe: slice 0 (System, 30%) lies in the top-right quadrant.
    c = make("", [("a", 30), ("b", 70, "#0000ff")], 0, YChartLegendPosition.Hidden)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    pcr = cairo.Context(surf)
    paint(c, pcr)
    area = c.get_backend_widget()
    cx, cy, r = area._center[0], area._center[1], area._radius
    surf.flush()
    data, stride = surf.get_data(), surf.get_stride()

    def px(x, y):
        o = int(y) * stride + int(x) * 4
        b, g, rr, a = data[o], data[o + 1], data[o + 2], data[o + 3]
        return rr, g, b, a
    check("pixel: top-right is palette[0]", px(cx + r / 2, cy - r / 2)[:3] == (0xe6, 0x9f, 0x00), px(cx + r / 2, cy - r / 2))
    check("pixel: bottom-left is custom blue", px(cx - r / 2, cy + r / 2)[:3] == (0, 0, 255), px(cx - r / 2, cy + r / 2))
    check("pixel: outside is transparent", px(cx + r + 3, cy)[3] == 0)

    # -- input ---------------------------------------------------------------
    c = make("Disk", [("a", 25), ("b", 25), ("c", 25), ("d", 25)], 0, YChartLegendPosition.Right)
    area = c.get_backend_widget()
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    paint(c, cairo.Context(surf))
    cx, cy, r = area._center[0], area._center[1], area._radius
    check("layout: radius > 0", r > 20, r)
    POSTED.clear()
    area._on_pressed(None, 1, cx + r / 2, cy + r / 2)
    check("click: bottom-right is slice b", c.selectedSlice() == 1 and len(POSTED) == 1, (c.selectedSlice(), len(POSTED)))
    (rx, ry, rw, rh), _idx = area._row_rects[3]
    area._on_pressed(None, 1, rx + rw / 2, ry + rh / 2)
    check("click: legend row d", c.selectedSlice() == 3 and len(POSTED) == 2)
    area._on_pressed(None, 1, 1, 1)
    check("click: outside does nothing", len(POSTED) == 2)
    area._on_key(None, Gdk.KEY_Right, 0, 0)
    check("key: right wraps to 0, no event", c.selectedSlice() == 0 and len(POSTED) == 2)
    check("key: Enter activates", area._on_key(None, Gdk.KEY_Return, 0, 0) and len(POSTED) == 3)
    check("key: other keys not consumed", not area._on_key(None, Gdk.KEY_a, 0, 0))
    c.setNotify(False)
    area._on_pressed(None, 1, cx - r / 2, cy + r / 2)
    check("notify off: selects, no event", c.selectedSlice() == 2 and len(POSTED) == 3)
    c.setNotify(True)
    c.setDonutRatio(0.6)
    paint(c, cairo.Context(surf))
    area._on_pressed(None, 1, cx, cy)
    check("donut: hole click ignored", len(POSTED) == 3)

    class _Tip:
        text = None

        def set_text(self, t):
            self.text = t
    tip = _Tip()
    c.setHelpText("help!")
    check("tooltip: slice text", area._on_query_tooltip(area, cx + r * 0.8, cy - r * 0.3, False, tip)
          and tip.text.startswith("a: 25"), tip.text)
    check("tooltip: help text elsewhere", area._on_query_tooltip(area, 1, 1, False, tip) and tip.text == "help!")

    # -- real window: GTK calls the draw func --------------------------------
    c = make("Window", [("x", 1), ("y", 2)], 0.4, YChartLegendPosition.Right, "3")
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
    check("window: natural size", area.get_content_width() > 200 and area.get_content_height() > 0,
          (area.get_content_width(), area.get_content_height()))
    n = len(calls)
    c.addSlice("z", 3)
    # Broadway without a connected browser throttles the frame clock.
    deadline = time.monotonic() + 3.0
    while len(calls) <= n and time.monotonic() < deadline:
        iterate(0.1)
    check("window: redraw on change", len(calls) > n)

    # -- many small changes: one deferred size update, not one per change ----
    sizes = []
    orig_size = area.update_size_request
    area.update_size_request = lambda: (sizes.append(1), orig_size())
    t0 = time.monotonic()
    for i in range(2000):
        c.addSlice(f"slice {i}", 1 + i % 5)
    check("addSlice x2000: no synchronous re-measure", not sizes and time.monotonic() - t0 < 2.0,
          (len(sizes), time.monotonic() - t0))
    iterate(0.3)
    check("addSlice x2000: one idle size update", len(sizes) == 1, len(sizes))
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    paint(c, cairo.Context(surf))
    check("dense pie paints", surf.status() == cairo.STATUS_SUCCESS if hasattr(surf, "status") else True)
    win.destroy()
    iterate(0.1)

    print("FAILED: " + ", ".join(FAILURES) if FAILURES else "all passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
