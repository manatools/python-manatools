#!/usr/bin/env python3

"""Headless check of the YChartGauge shared model (YChartGaugeBase).

No backend involved: defaults, range/value/band/target validation, angles
(clamping, sweep), nice ticks, band clipping and the value color, the fill
origin of ranges spanning zero, value text (decimals, unit, huge values),
tooltip and legend rows, fitting the dial into a box, hit testing and the
Activated event.

Run directly: python3 test/test_chartgauge_model_headless.py (exit 0 = pass).
"""

import math
import os
import sys

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from manatools.aui.yui import YChartBand, YChartLegendPosition  # noqa: E402
from manatools.aui.yui_common import YChartBase, YChartGaugeBase, YEventReason  # noqa: E402

FAILURES = []
POSTED = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
    if not cond:
        FAILURES.append(name)


def raises(exc, fn):
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


class _Dialog:
    def _post_event(self, ev):
        POSTED.append(ev)


class Gauge(YChartGaugeBase):
    redraws = 0

    def _apply_chart(self):
        Gauge.redraws += 1

    def findDialog(self):
        return _Dialog()


def close(a, b, eps=1e-9):
    return abs(a - b) < eps


def main():
    g = Gauge(None, "CPU")
    check("class", g.widgetClass() == "YChartGauge" and isinstance(g, YChartBase))
    check("defaults", g.minimum() == 0 and g.maximum() == 100 and g.value() == 0
          and g.sweepAngle() == 240 and g.decimals() == -1 and g.showValue() and g.showTicks()
          and not g.showNeedle() and g.target() is None and g.bandCount() == 0
          and g.unit() == "" and g.subtitle() == "" and g.valueColor() == g.DEFAULT_VALUE_COLOR
          and g.legendPosition() == YChartLegendPosition.Right)

    # -- validation ----------------------------------------------------------
    check("range must grow", raises(ValueError, lambda: g.setRange(5, 5))
          and raises(ValueError, lambda: g.setRange(10, 0)))
    check("range finite", raises(ValueError, lambda: g.setRange(0, float("inf")))
          and raises(ValueError, lambda: g.setRange(-1e301, 0)))
    check("bad value", raises(ValueError, lambda: g.setValue(float("nan")))
          and raises(TypeError, lambda: g.setValue(True)))
    check("sweep limits", raises(ValueError, lambda: g.setSweepAngle(179))
          and raises(ValueError, lambda: g.setSweepAngle(301)))
    check("decimals limits", raises(ValueError, lambda: g.setDecimals(7))
          and raises(ValueError, lambda: g.setDecimals(-2))
          and raises(TypeError, lambda: g.setDecimals(1.0))
          and raises(TypeError, lambda: g.setDecimals(True)))
    check("band start < end", raises(ValueError, lambda: g.addBand(5, 5))
          and raises(ValueError, lambda: g.addBand(0, 1, "red")))
    check("bad target", raises(ValueError, lambda: g.setTarget(float("nan"))))
    check("bad band index", raises(IndexError, lambda: g.band(0))
          and raises(TypeError, lambda: g.removeBand("0")))
    check("setBands atomic", raises(ValueError, lambda: g.setBands([(0, 10), (5, 1)]))
          and g.bandCount() == 0)
    check("state untouched by errors", g.minimum() == 0 and g.maximum() == 100 and g.sweepAngle() == 240)

    # -- angles ---------------------------------------------------------------
    check("angle ends", close(g._angle_of(0), -120) and close(g._angle_of(100), 120)
          and close(g._angle_of(50), 0))
    check("angle clamped", close(g._angle_of(-5), -120) and close(g._angle_of(1e300), 120))
    g.setSweepAngle(180)
    check("half circle", close(g._angle_of(0), -90) and close(g._angle_of(100), 90))
    g.setSweepAngle(240)

    # -- ticks ----------------------------------------------------------------
    t = g._ticks()
    check("ticks 0..100", [v for v, _, _ in t] == [0, 20, 40, 60, 80, 100], t)
    check("tick text + angle", t[1][2] == "20" and close(t[1][1], -72))
    g.setRange(-50, 50)
    vals = [v for v, _, _ in g._ticks()]
    check("ticks keep ends, drop crowded inner", vals == [-50, -20, 0, 20, 50], vals)
    g.setRange(0, 9)
    vals = [v for v, _, _ in g._ticks()]
    check("ticks odd range", vals == [0, 2, 4, 6, 9], vals)
    g.setRange(0, 2e9)
    check("tick format big", g._ticks()[-1][2] == "2G", g._ticks())
    g.setRange(0.1, 0.1000001)
    t = g._ticks()
    check("tick tiny range", t[0][0] == 0.1 and t[-1][0] == 0.1000001 and len(t) <= 10, t)
    g.setRange(-1e300, 1e300)
    t = g._ticks()
    check("tick extreme range", all(math.isfinite(a) for _, a, _ in t) and len(t) >= 2, t)
    g.setRange(0, 100)

    # -- bands and value color --------------------------------------------------
    redraws = Gauge.redraws
    g.setBands([(0, 60, None, "OK"), (60, 85, "#E69F00", "Warning"), (85, 120, None, "Critical")])
    check("setBands one redraw", Gauge.redraws == redraws + 1)
    check("band object", isinstance(g.band(1), YChartBand) and g.band(1).color() == "#e69f00"
          and g.band(1).label() == "Warning" and g.band(2).end() == 120)
    check("band palette", g.bandColor(0) == g.BAND_PALETTE[0] and g.bandColor(2) == g.BAND_PALETTE[2])
    arcs = g._band_arcs()
    check("band clipped to range", len(arcs) == 3 and close(arcs[2][2], 120)
          and close(arcs[2][1], g._angle_of(85)), arcs)
    g.setValue(72)
    check("value in band", g._current_color() == "#e69f00")
    g.setValue(60)
    check("overlap: later band wins", g._current_color() == "#e69f00")
    g.setValue(500)
    check("above range uses clamped value", g._current_color() == g.BAND_PALETTE[2])
    g.addBand(200, 300, None, "Off-dial")
    check("band outside range skipped", len(g._band_arcs()) == 3)
    g.removeBand(3)
    g.deleteAllBands()
    g.setValue(10)
    check("no band: valueColor", g._current_color() == g.DEFAULT_VALUE_COLOR)
    g.setValueColor("#123456")
    check("custom valueColor", g._current_color() == "#123456" and g.valueColor() == "#123456")
    g.setValueColor(None)

    # -- value arc and fill origin --------------------------------------------------
    a0, a1, _ = g._value_arc()
    check("arc from minimum", close(a0, -120) and close(a1, g._angle_of(10)))
    g.setRange(-50, 50)
    g.setValue(-25)
    a0, a1, _ = g._value_arc()
    check("arc from zero, negative value", close(a0, g._angle_of(-25)) and close(a1, 0))
    g.setRange(-100, -10)
    check("all-negative range fills from minimum", g._fill_origin() == -100)
    g.setRange(0, 100)

    # -- target -------------------------------------------------------------
    g.setTarget(90)
    check("target angle", g.target() == 90 and close(g._target_angle(), g._angle_of(90)))
    g.setTarget(150)
    check("target outside range not drawn", g.target() == 150 and g._target_angle() is None)
    g.setTarget(None)
    check("target cleared", g.target() is None and g._target_angle() is None)

    # -- text ---------------------------------------------------------------------
    g.setValue(72.456)
    check("auto decimals", g._value_text() == "72.46", g._value_text())
    g.setDecimals(1)
    g.setUnit(" GB")
    check("fixed decimals + unit", g._value_text() == "72.5 GB", g._value_text())
    g.setDecimals(0)
    g.setUnit("%")
    check("zero decimals", g._value_text() == "72%")
    g.setValue(1e300)
    check("huge value stays short", len(g._value_text()) < 20, g._value_text())
    g.setValue(72)
    g.setBands([(60, 85, None, "Warning <b>")])
    g.setTarget(90)
    tip = g._tooltip()
    check("tooltip", tip == "CPU: 72% (Warning <b>)\nTarget: 90%", tip)
    g.addBand(85, 100)
    rows = g._legend_rows()
    check("legend: labelled bands only", rows == [(0, "Warning <b>", "60..85", g.bandColor(0))], rows)

    # -- dial fitting and hit test --------------------------------------------
    cx, cy, r = g._dial_fit(200, 300)
    check("fit: width bound", close(r, 100) and close(cx, 100) and close(cy, 175))
    cx, cy, r = g._dial_fit(400, 150)
    check("fit: height bound (240)", close(r, 100) and close(cy, 100) and close(cx, 200))
    g.setSweepAngle(180)
    cx, cy, r = g._dial_fit(400, 150)
    check("fit: half circle is wide", close(r, 150) and close(cy, 150))
    check("hit: half circle", g._dial_hit(0, -100, 150) and not g._dial_hit(0, 50, 150)
          and not g._dial_hit(200, 0, 150))
    g.setSweepAngle(240)
    check("hit: 240 reaches below center", g._dial_hit(0, 40, 100) and not g._dial_hit(0, 60, 100))
    check("fit: empty box", g._dial_fit(0, 0)[2] == 0)

    # -- events -----------------------------------------------------------------
    POSTED.clear()
    check("click posts Activated", g._gauge_clicked() and len(POSTED) == 1
          and POSTED[0].widget() is g and POSTED[0].reason() == YEventReason.Activated)
    g.setNotify(False)
    g._gauge_clicked()
    check("notify off: no event", len(POSTED) == 1)
    g.setNotify(True)
    g.setEnabled(False)
    check("disabled: ignored", not g._gauge_clicked() and len(POSTED) == 1)
    g.setEnabled(True)

    # -- every setter redraws ------------------------------------------------------
    calls = [lambda: g.setRange(0, 10), lambda: g.setValue(1), lambda: g.setUnit("x"),
             lambda: g.setDecimals(2), lambda: g.setShowValue(False), lambda: g.setSubtitle("s"),
             lambda: g.setSweepAngle(200), lambda: g.setShowNeedle(True), lambda: g.setShowTicks(False),
             lambda: g.setValueColor("#000000"), lambda: g.setTarget(3), lambda: g.addBand(0, 1),
             lambda: g.removeBand(0), lambda: g.deleteAllBands(), lambda: g.setLabel("t")]
    ok = True
    for fn in calls:
        before = Gauge.redraws
        fn()
        ok = ok and Gauge.redraws == before + 1
    check("every setter redraws once", ok)
    g._ticks()
    v = g._version
    g.setRange(0, 1000)
    check("caches dropped on change", g._version == v + 1 and g._ticks()[-1][0] == 1000)

    print("FAILED: " + ", ".join(FAILURES) if FAILURES else "all passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
