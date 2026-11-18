#!/usr/bin/env python3

"""Headless check of YChartGauge on the Qt backend (QT_QPA_PLATFORM=offscreen).

Paints sample gauges (sweeps 180/240/300, needle, bands, target, legend
right/bottom/hidden, ranges spanning zero, long value text), optionally
saving them to a PNG for a visual check; checks pixel colors of the value
arc and the track; then drives the widget with synthetic mouse/key events:
clicks on and off the dial, Enter/Space, notify(False), disabled state,
literal tooltips.

No display needed.  Run directly:
    python3 test/test_chartgauge_qt_headless.py [out.png]
(exit 0 = pass).
"""

import math
import os
import sys

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6 import QtWidgets, QtCore, QtGui  # noqa: E402

from manatools.aui.yui_common import YChartLegendPosition, YEventReason  # noqa: E402
from manatools.aui.backends.qt.chartgaugeqt import YChartGaugeQt  # noqa: E402

W, H = 420, 260
FAILURES = []
POSTED = []
BANDS = [(0, 60, None, "OK"), (60, 85, None, "Warning"), (85, 100, None, "Critical")]


class QTest:
    """Minimal stand-in: PySide6 builds do not always ship QtTest."""
    @staticmethod
    def mouseClick(w, pos):
        pf = QtCore.QPointF(pos)
        b = QtCore.Qt.MouseButton.LeftButton
        for t in (QtCore.QEvent.Type.MouseButtonPress, QtCore.QEvent.Type.MouseButtonRelease):
            ev = QtGui.QMouseEvent(t, pf, w.mapToGlobal(pf), b, b, QtCore.Qt.KeyboardModifier.NoModifier)
            QtWidgets.QApplication.sendEvent(w, ev)

    @staticmethod
    def keyClick(w, key):
        QtWidgets.QApplication.sendEvent(w, QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, key,
                                                            QtCore.Qt.KeyboardModifier.NoModifier))


class _Dialog:
    def _post_event(self, ev):
        POSTED.append(ev)


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
    if not cond:
        FAILURES.append(name)


app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def make(label="CPU", value=72, sweep=240, needle=False, bands=BANDS, target=90,
         legend=YChartLegendPosition.Right, unit="%", subtitle="load", rng=None):
    g = YChartGaugeQt(None, label)
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
    w = g.get_backend_widget()
    w.resize(W, H)
    w.show()
    app.processEvents()
    w.grab()        # paint once so the dial layout is known
    return g, w


def polar(w, angle, frac):
    a = math.radians(angle)
    r = w._radius * frac
    return QtCore.QPointF(w._center.x() + r * math.sin(a), w._center.y() - r * math.cos(a))


def pixel(img, pt):
    return img.pixelColor(pt.toPoint())


def near(c, hex_color, tol=40):
    q = QtGui.QColor(hex_color)
    return abs(c.red() - q.red()) + abs(c.green() - q.green()) + abs(c.blue() - q.blue()) <= tol


def main():
    cases = [
        dict(),
        dict(needle=True, legend=YChartLegendPosition.Bottom),
        dict(sweep=180, legend=YChartLegendPosition.Hidden),
        dict(sweep=180, needle=True),
        dict(sweep=300, value=1234.5, unit=" GB", bands=[], rng=(0, 2000), target=None, subtitle=""),
        dict(sweep=300, needle=True, value=-20, rng=(-50, 50), label="", target=25),
    ]
    gauges = [make(**kw) for kw in cases]      # keep owners alive: the canvas holds a weakref
    shots = [w.grab().toImage() for _g, w in gauges]
    img = QtGui.QImage(W, H * len(shots), QtGui.QImage.Format.Format_ARGB32)
    img.fill(QtGui.QColor("white"))
    p = QtGui.QPainter(img)
    for i, s in enumerate(shots):
        p.drawImage(0, H * i, s)
        p.setPen(QtGui.QColor("#888"))
        p.drawLine(0, H * i, W, H * i)
    p.end()
    if len(sys.argv) > 1:
        img.save(sys.argv[1])
    check("paint: all samples", all(not s.isNull() for s in shots))

    # -- pixels --------------------------------------------------------------
    g, w = gauges[0]
    shot = w.grab().toImage()
    check("layout: dial fits", w._radius > 50 and w._center.x() < W, (w._radius, w._center))
    mid = (0.70 + 0.90) / 2
    check("pixel: value arc in band color", near(pixel(shot, polar(w, g._angle_of(30), mid)), "#e69f00"),
          pixel(shot, polar(w, g._angle_of(30), mid)).name())
    check("pixel: track beyond value", not near(pixel(shot, polar(w, g._angle_of(80), mid)), "#e69f00"))
    check("pixel: band ring", near(pixel(shot, polar(w, g._angle_of(95), 0.97)), "#d55e00"),
          pixel(shot, polar(w, g._angle_of(95), 0.97)).name())
    g5, w5 = gauges[5]
    shot5 = w5.grab().toImage()
    check("pixel: zero-spanning range fills from 0", near(pixel(shot5, polar(w5, g5._angle_of(-10), mid)),
                                                       g5.DEFAULT_VALUE_COLOR)
          and not near(pixel(shot5, polar(w5, g5._angle_of(-35), mid)), g5.DEFAULT_VALUE_COLOR))

    # -- clicks ----------------------------------------------------------------
    POSTED.clear()
    QTest.mouseClick(w, polar(w, 0, 0.5).toPoint())
    check("click: dial posts Activated", len(POSTED) == 1 and POSTED[0].widget() is g
          and POSTED[0].reason() == YEventReason.Activated)
    QTest.mouseClick(w, QtCore.QPoint(2, H - 2))
    check("click: outside dial ignored", len(POSTED) == 1)
    w.setFocus()
    QTest.keyClick(w, QtCore.Qt.Key.Key_Return)
    QTest.keyClick(w, QtCore.Qt.Key.Key_Space)
    check("keys: Enter/Space activate", len(POSTED) == 3)
    QTest.keyClick(w, QtCore.Qt.Key.Key_A)
    check("keys: others ignored", len(POSTED) == 3)
    g.setNotify(False)
    QTest.mouseClick(w, polar(w, 0, 0.5).toPoint())
    check("notify off: no event", len(POSTED) == 3)
    g.setNotify(True)
    g.setEnabled(False)
    app.processEvents()
    QTest.mouseClick(w, polar(w, 0, 0.5).toPoint())
    check("disabled: no event", len(POSTED) == 3 and not w.isEnabled())
    g.setEnabled(True)

    # -- tooltip ------------------------------------------------------------------
    g.setLabel("<b>CPU</b>")
    shown = []
    orig = QtWidgets.QToolTip.showText
    QtWidgets.QToolTip.showText = lambda pos, text, *a: shown.append(text)
    try:
        pos = polar(w, 0, 0.5).toPoint()
        ev = QtGui.QHelpEvent(QtCore.QEvent.Type.ToolTip, pos, w.mapToGlobal(pos))
        w.event(ev)
    finally:
        QtWidgets.QToolTip.showText = orig
    check("tooltip: literal label", shown and "&lt;b&gt;CPU&lt;/b&gt;: 72%" in shown[0]
          and "Warning" in shown[0], shown)

    # -- live update ---------------------------------------------------------------
    g.setValue(95)
    shot = w.grab().toImage()
    check("update: value color follows band", near(pixel(shot, polar(w, g._angle_of(30), mid)), "#d55e00"))
    check("size hints", w.sizeHint().width() > 0 and w.minimumSizeHint().height() > 0)

    print("FAILED: " + ", ".join(FAILURES) if FAILURES else "all passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
