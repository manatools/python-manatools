#!/usr/bin/env python3

"""Automated check of YChartGauge on the GTK backend.

Needs a GDK display but no interaction; a headless one works:

    gtk4-broadwayd :5 &
    GDK_BACKEND=broadway BROADWAY_DISPLAY=:5 python3 test/test_chartgauge_gtk_headless.py [out.png]

Paints sample gauges (sweeps 180/240/300, needle, bands, target, legend
right/bottom/hidden, a range spanning zero, long value text) into a cairo
image surface, optionally saved to PNG for a visual check; probes pixel
colors of the value arc, track and band ring; shows one gauge in a real
Gtk.Window to make sure GTK draws it; and drives the input handlers:
clicks on and off the dial, Enter/Space, notify(False), query-tooltip.

Exit code 0 = pass.
"""

import math
import os
import sys
import time

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import gi  # noqa: E402
gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk, Gdk  # noqa: E402
import cairo  # noqa: E402

from manatools.aui.yui_common import YChartLegendPosition, YEventReason  # noqa: E402
from manatools.aui.backends.gtk.chartgaugegtk import YChartGaugeGtk  # noqa: E402

W, H = 420, 260
FAILURES = []
POSTED = []
WINDOWS = []
BANDS = [(0, 60, None, "OK"), (60, 85, None, "Warning"), (85, 100, None, "Critical")]


class _Dialog:
    def _post_event(self, ev):
        POSTED.append(ev)


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
    if not cond:
        FAILURES.append(name)


def make(label="CPU", value=72, sweep=240, needle=False, bands=BANDS, target=90,
         legend=YChartLegendPosition.Right, unit="%", subtitle="load", rng=None):
    g = YChartGaugeGtk(None, label)
    g.findDialog = lambda: _Dialog()
    if rng:
        g.setRange(*rng)
    g.setBands(bands)
    g.setValue(value)
    g.setSweepAngle(sweep)
    g.setShowNeedle(needle)
    g.setTarget(target)
    g.setLegendPosition(legend)
    g.setUnit(unit)
    g.setSubtitle(subtitle)
    g._create_backend_widget()
    # Root the area so it gets the theme's style (text color) when painted.
    win = Gtk.Window()
    win.set_child(g.get_backend_widget())
    WINDOWS.append(win)
    return g


def paint(g, cr):
    g.get_backend_widget().paint(cr, g, W, H)


def snapshot(g):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    paint(g, cairo.Context(surf))
    surf.flush()
    return surf


def px(surf, x, y):
    data, stride = surf.get_data(), surf.get_stride()
    o = int(y) * stride + int(x) * 4
    b, g, r, a = data[o], data[o + 1], data[o + 2], data[o + 3]
    return r, g, b, a


def near(rgba, hex_color, tol=40):
    want = tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return rgba[3] > 200 and sum(abs(a - b) for a, b in zip(rgba[:3], want)) <= tol


def polar(g, angle, frac):
    area = g.get_backend_widget()
    (cx, cy), r = area._center, area._radius * frac
    a = math.radians(angle)
    return cx + r * math.sin(a), cy - r * math.cos(a)


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
        dict(),
        dict(needle=True, legend=YChartLegendPosition.Bottom),
        dict(sweep=180, legend=YChartLegendPosition.Hidden),
        dict(sweep=180, needle=True),
        dict(sweep=300, value=1234.5, unit=" GB", bands=[], rng=(0, 2000), target=None, subtitle=""),
        dict(sweep=300, needle=True, value=-20, rng=(-50, 50), label="", target=25),
    ]
    sheet = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H * len(cases))
    cr = cairo.Context(sheet)
    cr.set_source_rgb(0.94, 0.94, 0.94)
    cr.paint()
    gauges = []
    for i, kw in enumerate(cases):
        g = make(**kw)
        gauges.append(g)
        cr.save()
        cr.translate(0, H * i)
        paint(g, cr)
        cr.restore()
        cr.set_source_rgb(0.55, 0.55, 0.55)
        cr.rectangle(0, H * i, W, 1)
        cr.fill()
    if len(sys.argv) > 1:
        sheet.write_to_png(sys.argv[1])
    check("paint: all samples", sheet.status() == cairo.STATUS_SUCCESS if hasattr(sheet, "status") else True)

    # -- pixels --------------------------------------------------------------
    g = gauges[0]
    surf = snapshot(g)
    area = g.get_backend_widget()
    check("layout: dial fits", area._radius > 50, area._radius)
    mid = (0.70 + 0.90) / 2
    check("pixel: value arc in band color", near(px(surf, *polar(g, g._angle_of(30), mid)), "#e69f00"),
          px(surf, *polar(g, g._angle_of(30), mid)))
    check("pixel: track beyond value", not near(px(surf, *polar(g, g._angle_of(80), mid)), "#e69f00"))
    check("pixel: band ring", near(px(surf, *polar(g, g._angle_of(95), 0.97)), "#d55e00"),
          px(surf, *polar(g, g._angle_of(95), 0.97)))
    g5 = gauges[5]
    surf5 = snapshot(g5)
    check("pixel: zero-spanning range fills from 0",
          near(px(surf5, *polar(g5, g5._angle_of(-10), mid)), g5.DEFAULT_VALUE_COLOR)
          and not near(px(surf5, *polar(g5, g5._angle_of(-35), mid)), g5.DEFAULT_VALUE_COLOR))

    # -- input ---------------------------------------------------------------
    POSTED.clear()
    area._on_pressed(None, 1, *polar(g, 0, 0.5))
    check("click: dial posts Activated", len(POSTED) == 1 and POSTED[0].widget() is g
          and POSTED[0].reason() == YEventReason.Activated)
    area._on_pressed(None, 1, 2, H - 2)
    check("click: outside dial ignored", len(POSTED) == 1)
    check("key: Enter activates", area._on_key(None, Gdk.KEY_Return, 0, 0) and len(POSTED) == 2)
    check("key: Space activates", area._on_key(None, Gdk.KEY_space, 0, 0) and len(POSTED) == 3)
    check("key: others not consumed", not area._on_key(None, Gdk.KEY_a, 0, 0))
    g.setNotify(False)
    area._on_pressed(None, 1, *polar(g, 0, 0.5))
    check("notify off: no event", len(POSTED) == 3)
    g.setNotify(True)
    g.setEnabled(False)
    area._on_pressed(None, 1, *polar(g, 0, 0.5))
    check("disabled: no event", len(POSTED) == 3 and not area.is_sensitive())
    g.setEnabled(True)

    class _Tip:
        text = None

        def set_text(self, t):
            self.text = t
    tip = _Tip()
    g.setHelpText("help!")
    check("tooltip: value text", area._on_query_tooltip(area, *polar(g, 0, 0.5), False, tip)
          and tip.text == "CPU: 72% (Warning)\nTarget: 90%", tip.text)
    check("tooltip: help text elsewhere", area._on_query_tooltip(area, 1, H - 1, False, tip)
          and tip.text == "help!")

    g.setValue(95)
    surf = snapshot(g)
    check("update: value color follows band", near(px(surf, *polar(g, g._angle_of(30), mid)), "#d55e00"))

    # -- real window: GTK calls the draw func --------------------------------
    g = make("Window")
    calls = []
    area = g.get_backend_widget()
    orig = area.paint
    area.paint = lambda *a: (calls.append(a[2:]), orig(*a))
    win = area.get_root()
    win.set_default_size(W, H)
    win.present()
    deadline = time.monotonic() + 3.0
    while not calls and time.monotonic() < deadline:
        iterate(0.1)
    check("window: draw func called", bool(calls), calls)
    check("window: natural size", area.get_content_width() > 200 and area.get_content_height() > 100,
          (area.get_content_width(), area.get_content_height()))
    n = len(calls)
    g.setValue(10)
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
