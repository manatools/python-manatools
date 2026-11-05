#!/usr/bin/env python3

"""Headless check of YChartBar on the Qt backend (QT_QPA_PLATFORM=offscreen).

Paints sample charts (grouped/stacked, vertical/horizontal, negatives, value
labels, many categories, empty), optionally saving them to a PNG for a visual
check, and drives the widget with synthetic mouse/key events: bar clicks in
both orientations and in stacked mode, clicks on empty plot space, arrow
keys along categories/series, Enter, notify(False), disabled state.

No display needed.  Run directly:
    python3 test/test_chartbar_qt_headless.py [out.png]
(exit 0 = pass).
"""

import os
import sys

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6 import QtWidgets, QtCore, QtGui  # noqa: E402

from manatools.aui.yui_common import YChartBarOrientation as O, YChartLegendPosition  # noqa: E402
from manatools.aui.backends.qt.chartbarqt import YChartBarQt  # noqa: E402

W, H = 460, 280
FAILURES = []
POSTED = []
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
ROWS = [[30, 20, 5], [45, 25, -8], [28, 40, 12], [60, 15, -20], [52, 33, 7], [80, 10, 15]]
SERIES = ["CPU", "RAM", ("Swap", "#cc0000")]


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


def make(label="Load", cats=MONTHS, series=SERIES, rows=ROWS, orientation=O.Vertical,
         stacked=False, values=False, legend=YChartLegendPosition.Right, sel=None):
    c = YChartBarQt(None, label)
    c.findDialog = lambda: _Dialog()
    c.setData(cats, series, rows)
    c.setOrientation(orientation)
    c.setStacked(stacked)
    c.setShowValues(values)
    c.setLegendPosition(legend)
    c._create_backend_widget()
    if sel:
        c.setSelectedBar(*sel)
    w = c.get_backend_widget()
    w.resize(W, H)
    w.show()
    app.processEvents()
    w.grab()        # paint once so the plot layout is known
    return c, w


def to_px(w, u, v):
    """Pixel of category-axis fraction *u* and value *v* in the last paint."""
    left, top, right, bottom, horizontal, vmin, span = w._plot
    if horizontal:
        return QtCore.QPointF(left + (v - vmin) / span * (right - left), top + u * (bottom - top))
    return QtCore.QPointF(left + u * (right - left), bottom - (v - vmin) / span * (bottom - top))


def centre(c, w, cat, ser):
    for cc, s, u0, u1, v0, v1, _col in c._bar_geometry():
        if (cc, s) == (cat, ser):
            return to_px(w, (u0 + u1) / 2, (v0 + v1) / 2).toPoint()
    raise KeyError((cat, ser))


def main():
    cases = [
        dict(values=True, sel=(3, 0)),
        dict(stacked=True, values=True, legend=YChartLegendPosition.Bottom),
        dict(orientation=O.Horizontal, values=True, sel=(1, 2)),
        dict(orientation=O.Horizontal, stacked=True),
        dict(label="", cats=[f"Category {i}" for i in range(40)], series=["s"],
             rows=[[(i * 37) % 50 - 10] for i in range(40)]),
        dict(label="Empty", cats=[], series=[], rows=[]),
    ]
    charts = [make(**kw) for kw in cases]      # keep owners alive: the canvas holds a weakref
    shots = [w.grab().toImage() for _c, w in charts]
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

    # -- clicks, vertical grouped ---------------------------------------------
    c, w = make()
    check("layout: plot known", w._plot is not None)
    POSTED.clear()
    QTest.mouseClick(w, centre(c, w, 2, 1))
    check("click: bar (Mar, RAM)", (c.selectedCategory(), c.selectedSeries()) == (2, 1) and len(POSTED) == 1,
          (c.selectedCategory(), c.selectedSeries(), len(POSTED)))
    QTest.mouseClick(w, centre(c, w, 3, 2))
    check("click: negative bar", (c.selectedCategory(), c.selectedSeries()) == (3, 2) and len(POSTED) == 2)
    QTest.mouseClick(w, to_px(w, 0.08, 75).toPoint())
    check("click: empty plot space does nothing", len(POSTED) == 2)
    QTest.mouseClick(w, QtCore.QPoint(2, 2))
    check("click: outside plot does nothing", len(POSTED) == 2)

    # -- keys ----------------------------------------------------------------
    w.setFocus()
    QTest.keyClick(w, QtCore.Qt.Key.Key_Right)
    check("key: Right moves category, no event", (c.selectedCategory(), c.selectedSeries()) == (4, 2)
          and len(POSTED) == 2)
    QTest.keyClick(w, QtCore.Qt.Key.Key_Down)
    check("key: Down moves series", c.selectedSeries() == 1)
    QTest.keyClick(w, QtCore.Qt.Key.Key_Return)
    check("key: Enter activates", len(POSTED) == 3)
    c.setNotify(False)
    QTest.mouseClick(w, centre(c, w, 0, 0))
    check("notify off: selects, no event", (c.selectedCategory(), c.selectedSeries()) == (0, 0)
          and len(POSTED) == 3)
    c.setNotify(True)
    c.setEnabled(False)
    QTest.mouseClick(w, centre(c, w, 1, 0))
    check("disabled: no event", len(POSTED) == 3)

    # -- horizontal + stacked ------------------------------------------------
    c, w = make(orientation=O.Horizontal, stacked=True)
    POSTED.clear()
    QTest.mouseClick(w, centre(c, w, 5, 1))
    check("horizontal stacked: segment click", (c.selectedCategory(), c.selectedSeries()) == (5, 1)
          and len(POSTED) == 1, (c.selectedCategory(), c.selectedSeries()))
    w.setFocus()
    QTest.keyClick(w, QtCore.Qt.Key.Key_Up)
    check("horizontal: Up moves category", c.selectedCategory() == 4)
    QTest.keyClick(w, QtCore.Qt.Key.Key_Right)
    check("horizontal: Right moves series", c.selectedSeries() == 2)

    c, w = make(cats=[], series=[], rows=[])
    w.setFocus()
    QTest.keyClick(w, QtCore.Qt.Key.Key_Right)
    check("empty: keys ignored", (c.selectedCategory(), c.selectedSeries()) == (-1, -1))
    check("sizeHint sane", w.sizeHint().width() >= 240 and w.minimumSizeHint().height() > 0, w.sizeHint())

    print("FAILED: " + ", ".join(FAILURES) if FAILURES else "all passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
