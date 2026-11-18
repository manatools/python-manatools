#!/usr/bin/env python3

"""Headless check of the YChartBar shared model (YChartBarBase).

No backend involved: series/category bookkeeping, validation, the value axis
(nice steps, zero always included, stacked sums), bar geometry for grouped
and stacked layouts with negative values, hit testing, tick/tooltip text,
selection bookkeeping and the Activated event.

Run directly: python3 test/test_chartbar_model_headless.py (exit 0 = pass).
"""

import os
import sys

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from manatools.aui.yui import YChartBarOrientation, YChartLegendPosition  # noqa: E402
from manatools.aui.yui_common import YChartBarBase, YChartBase, YChartPieBase, YEventReason  # noqa: E402

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


class Chart(YChartBarBase):
    redraws = 0

    def _apply_chart(self):
        Chart.redraws += 1

    def findDialog(self):
        return _Dialog()


def close(a, b, eps=1e-9):
    return abs(a - b) < eps


def main():
    c = Chart(None, "Usage")
    check("class", c.widgetClass() == "YChartBar" and isinstance(c, YChartBase))
    check("defaults", c.orientation() == YChartBarOrientation.Vertical and not c.stacked()
          and not c.showValues() and c.showGrid() and c.legendPosition() == YChartLegendPosition.Right)

    # -- bookkeeping ---------------------------------------------------------
    check("addSeries index", c.addSeries("CPU") == 0 and c.addSeries("RAM", "#FF0000") == 1)
    check("addCategory index", c.addCategory("Jan", [10, 20]) == 0 and c.addCategory("Feb", [5]) == 1)
    check("missing value = 0", c.value(1, 1) == 0.0)
    check("series color", c.seriesColor(0) == c.PALETTE[0] and c.seriesColor(1) == "#ff0000")
    c.addSeries("Disk")
    check("new series padded", c.value(0, 2) == 0.0 and c.value(1, 2) == 0.0)
    c.setValue(1, 2, -7.5)
    check("negative value", c.value(1, 2) == -7.5 and c.categoryTotal(1) == -2.5)
    check("bad value", raises(ValueError, lambda: c.setValue(0, 0, float("nan")))
          and raises(TypeError, lambda: c.setValue(0, 0, True)))
    check("bad index", raises(IndexError, lambda: c.value(5, 0)) and raises(TypeError, lambda: c.value("0", 0)))
    check("too many values", raises(ValueError, lambda: c.addCategory("x", [1, 2, 3, 4])))
    check("bad color", raises(ValueError, lambda: c.addSeries("x", "red")))

    c.setSelectedBar(1, 2)
    c.removeSeries(0)
    check("removeSeries shifts selection", (c.selectedCategory(), c.selectedSeries()) == (1, 1))
    c.removeCategory(0)
    check("removeCategory shifts selection", (c.selectedCategory(), c.selectedSeries()) == (0, 1))
    c.removeCategory(0)
    check("remove selected clears", (c.selectedCategory(), c.selectedSeries()) == (-1, -1))

    try:
        c.setData(["a", "b"], ["x", ("y", "#00ff00")], [[1, 2], [3, -4], [5]])
        ok = False
    except ValueError:
        ok = True
    check("setData: too many rows rejected, chart unchanged", ok and c.categoryCount() == 0
          and c.seriesCount() == 2)
    c.setData(["a", "b", "c"], ["x", ("y", "#00ff00")], [[1, 2], [3, -4]])
    check("setData", c.categoryCount() == 3 and c.seriesCount() == 2 and c.value(2, 1) == 0
          and c.seriesColor(1) == "#00ff00" and c.seriesName(0) == "x")
    c.deleteAllData()
    check("deleteAllData", c.categoryCount() == 0 and c.seriesCount() == 0 and c._bar_geometry() == [])
    check("empty axis 0..1", c._value_axis()[:2] == (0.0, 1.0), c._value_axis())

    # -- axis ----------------------------------------------------------------
    c.setData(["a"], ["s"], [[87]])
    vmin, vmax, ticks = c._value_axis()
    check("axis: 0..100 by 20", (vmin, vmax) == (0, 100) and ticks == [0, 20, 40, 60, 80, 100], (vmin, vmax, ticks))
    c.setData(["a", "b"], ["s"], [[-0.3], [0.72]])
    vmin, vmax, ticks = c._value_axis()
    check("axis: fractional with negatives", close(vmin, -0.4) and close(vmax, 0.8) and 0.0 in ticks
          and len(ticks) == 7, (vmin, vmax, ticks))
    c.setData(["a"], ["s"], [[-1234]])
    vmin, vmax, ticks = c._value_axis()
    check("axis: all negative keeps 0 on top", vmax == 0 and vmin <= -1234, (vmin, vmax, ticks))
    c.setData(["a", "b"], ["p", "q"], [[30, 40], [-10, 25]])
    grouped = c._value_axis()
    c.setStacked(True)
    stacked = c._value_axis()
    check("axis: stacked uses sums", grouped[:2] == (-10, 40) and stacked[1] >= 70 and stacked[1] < 100
          and stacked[0] <= -10,
          (grouped, stacked))

    # -- geometry ------------------------------------------------------------
    c.setStacked(False)
    g = c._bar_geometry()
    check("grouped: 4 bars", len(g) == 4)
    a_p, a_q = g[0], g[1]
    check("grouped: slot layout", close(a_p[2], 0.05) and close(a_p[3], 0.25)
          and close(a_q[2], 0.25) and close(a_q[3], 0.45), (a_p, a_q))
    check("grouped: baseline 0", a_p[4:6] == (0.0, 30.0))
    b_p = g[2]
    check("grouped: negative goes down", b_p[:2] == (1, 0) and b_p[4:6] == (0.0, -10.0))
    c.setStacked(True)
    g = c._bar_geometry()
    a_q = [b for b in g if b[:2] == (0, 1)][0]
    check("stacked: piles up", close(a_q[2], 0.05) and close(a_q[3], 0.45) and a_q[4:6] == (30.0, 70.0), a_q)
    b_p, b_q = [b for b in g if b[0] == 1]
    check("stacked: negatives apart", b_p[4:6] == (0.0, -10.0) and b_q[4:6] == (0.0, 25.0), (b_p, b_q))
    c.setValue(0, 0, 0)
    check("zero values skipped", not [b for b in c._bar_geometry() if b[:2] == (0, 0)])

    # -- hit test ------------------------------------------------------------
    c.setData(["a", "b"], ["p", "q"], [[30, 40], [-10, 25]])
    c.setStacked(False)
    check("hit: grouped bar", c._bar_at(0.1, 15) == (0, 0) and c._bar_at(0.3, 39) == (0, 1))
    check("hit: above bar misses", c._bar_at(0.1, 31) == (-1, -1))
    check("hit: negative bar", c._bar_at(0.6, -5) == (1, 0))
    check("hit: slot padding misses", c._bar_at(0.01, 5) == (-1, -1))
    check("hit: tolerance reaches a thin bar", c._bar_at(0.04, 5, 0.02) == (0, 0)
          and c._bar_at(0.04, 5) == (-1, -1))
    check("hit: tolerance picks nearest center", c._bar_at(0.249, 15, 0.05) == (0, 0)
          and c._bar_at(0.251, 15, 0.05) == (0, 1))
    c.setStacked(True)
    check("hit: stacked segment", c._bar_at(0.2, 50) == (0, 1) and c._bar_at(0.2, 10) == (0, 0))
    check("category at", c._category_at(0.75) == 1 and c._category_at(1.0) == -1)

    # -- text ----------------------------------------------------------------
    check("tick format", [c._format_tick(v) for v in (0, 2.5, 1500, -20e6, 3e9, 0.05)]
          == ["0", "2.5", "1.5k", "-20M", "3G", "0.05"],
          [c._format_tick(v) for v in (0, 2.5, 1500, -20e6, 3e9, 0.05)])
    check("tooltip", c._bar_tooltip(1, 0) == "b · p: -10", c._bar_tooltip(1, 0))
    c.setSeriesName(0, "")
    check("tooltip without series name", c._bar_tooltip(1, 0) == "b: -10")
    check("legend rows", c._legend_rows() == [(0, "", c.PALETTE[0]), (1, "q", c.PALETTE[1])])

    # -- click ---------------------------------------------------------------
    POSTED.clear()
    check("click posts Activated", c._bar_clicked(1, 1) and len(POSTED) == 1
          and POSTED[0].reason() == YEventReason.Activated and POSTED[0].widget() is c)
    check("click selects", (c.selectedCategory(), c.selectedSeries()) == (1, 1))
    check("bad clicks ignored", not c._bar_clicked(5, 0) and not c._bar_clicked("x", 0)
          and not c._bar_clicked(0, -1) and len(POSTED) == 1)
    c.setNotify(False)
    c._bar_clicked(0, 0)
    check("notify off: selects, no event", (c.selectedCategory(), c.selectedSeries()) == (0, 0) and len(POSTED) == 1)
    check("setSelectedBar validates", raises(IndexError, lambda: c.setSelectedBar(9, 0)))
    check("orientation type checked", raises(TypeError, lambda: c.setOrientation(1)))

    # -- limits (shared YChartBase checks) --------------------------------------
    check("values beyond MAX_VALUE rejected", raises(ValueError, lambda: c.setValue(0, 0, 1e301))
          and raises(ValueError, lambda: YChartPieBase(None).addSlice("x", 1e308)))
    for rows, stacked in (([[1e300], [-1e300]], False), ([[1e300]] * 4, True), ([[5e-324]], False),
                          ([[1e-300], [2e-300]], False)):
        x = Chart(None)
        x.setData([str(i) for i in range(len(rows))], ["s"], rows)
        x.setStacked(stacked)
        try:
            vmin, vmax, ticks = x._value_axis()
            ok = vmin <= min(0.0, min(r[0] for r in rows)) and vmax >= max(r[0] for r in rows) and len(ticks) >= 2
        except Exception as e:
            ok = repr(e)
        check(f"axis survives {rows[0][0]:g} (stacked={stacked})", ok is True, ok)
    check("huge ticks/values stay short", c._format_tick(2e299) == "2e+299"
          and YChartBase._format_value(1e300) == "1e+300" and YChartBase._format_value(0.001) == "0.001")
    pie = YChartPieBase(None)
    pie.setSlices([("a", 1e300), ("b", 1e300)])
    geom = pie._geometry()
    check("pie of huge values stays finite", pie.total() == 2e300 and len(geom) == 2
          and abs(geom[1][1] - 180.0) < 1e-9 and pie._legend_rows()[0][3] == "50.0%", geom)

    # -- caches and the selection hook --------------------------------------------
    pie.total()
    check("pie total cached", pie._total_cache == 2e300)
    v = pie._version
    pie.setSliceValue(0, 1)
    check("data change bumps version, drops caches", pie._version == v + 1 and pie._total_cache is None)
    rows1 = pie._legend_rows()
    check("legend rows cached", pie._legend_rows() is rows1)
    pie.setShowPercent(False)
    check("legend cache follows showPercent", pie._legend_rows()[0][3] == "")
    seen = []
    pie._apply_selection = lambda old: seen.append(("sel", old))
    pie._apply_chart = lambda: seen.append(("chart",))
    pie.setSelectedSlice(1)
    pie._slice_clicked(0)
    pie.setSelectedSlice(0)
    check("pie selection uses _apply_selection only on change", seen == [("sel", -1), ("sel", 1)], seen)
    c.setSelectedBar(-1, -1)
    seen.clear()
    c._apply_selection = lambda old: seen.append(("sel", old))
    c.setSelectedBar(0, 0)
    c._bar_clicked(1, 1)
    c.setSelectedBar(1, 1)
    check("bar selection uses _apply_selection only on change", seen == [("sel", (-1, -1)), ("sel", (0, 0))], seen)

    print("FAILED: " + ", ".join(FAILURES) if FAILURES else "all passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
