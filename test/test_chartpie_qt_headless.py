#!/usr/bin/env python3

"""Headless check of YChartPie on the Qt backend (QT_QPA_PLATFORM=offscreen).

Paints sample charts (pie, donut, single slice, empty, 30 slices), optionally
saving them to a PNG for a visual check, and drives the widget with synthetic
mouse/key events: slice and legend-row clicks, outside and donut-hole clicks,
arrow/Enter keys, notify(False) and disabled state.

No display needed.  Run directly:
    python3 test/test_chartpie_qt_headless.py [out.png]
(exit 0 = pass).
"""

import os
import sys

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6 import QtWidgets, QtCore, QtGui

class QTest:
    """Minimal stand-in: PySide6 builds do not always ship QtTest."""
    @staticmethod
    def mouseClick(w, button, pos):
        pf = QtCore.QPointF(pos)
        for t in (QtCore.QEvent.Type.MouseButtonPress, QtCore.QEvent.Type.MouseButtonRelease):
            ev = QtGui.QMouseEvent(t, pf, w.mapToGlobal(pf), button, button, QtCore.Qt.KeyboardModifier.NoModifier)
            QtWidgets.QApplication.sendEvent(w, ev)
    @staticmethod
    def keyClick(w, key):
        QtWidgets.QApplication.sendEvent(w, QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, key, QtCore.Qt.KeyboardModifier.NoModifier))
from manatools.aui.yui_common import YChartLegendPosition
from manatools.aui.backends.qt.chartpieqt import YChartPieQt
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
posted = []
class D:
    def _post_event(self, e): posted.append(e)
fails = []
def check(n, c, d=""):
    print(("ok   " if c else "FAIL ") + n + ("" if c else f"  {d}"))
    if not c: fails.append(n)

def make(label, slices, ratio=0.0, pos=YChartLegendPosition.Right, center="", sel=-1, size=(420, 260)):
    c = YChartPieQt(None, label)
    c.findDialog = lambda: D()
    c.setSlices(slices); c.setDonutRatio(ratio); c.setLegendPosition(pos); c.setCenterText(center)
    c._create_backend_widget()
    if sel >= 0: c.setSelectedSlice(sel)
    w = c.get_backend_widget(); w.resize(*size); w.show()
    app.processEvents()
    return c, w

shots = []
cases = [
    ("Disk usage", [("System", 30), ("Home & stuff", 10, "#ff0000"), ("Free", 60)], 0, YChartLegendPosition.Right, "", 1),
    ("Donut", [("a", 30), ("b", 10), ("c", 5), ("d", 55)], 0.55, YChartLegendPosition.Bottom, "100 GB", 3),
    ("", [("one", 1)], 0, YChartLegendPosition.Hidden, "", -1),
    ("Empty", [], 0, YChartLegendPosition.Right, "", -1),
    ("Many", [(f"slice number {i}", i + 1) for i in range(30)], 0.3, YChartLegendPosition.Right, "", 5),
]
for args in cases:
    c, w = make(*args)
    shots.append(w.grab().toImage())
img = QtGui.QImage(420, 260 * len(shots), QtGui.QImage.Format.Format_ARGB32)
img.fill(QtGui.QColor("white"))
p = QtGui.QPainter(img)
for i, s in enumerate(shots):
    p.drawImage(0, 260 * i, s)
    p.setPen(QtGui.QColor("#888")); p.drawLine(0, 260 * i, 420, 260 * i)
p.end()
if len(sys.argv) > 1:
    img.save(sys.argv[1])

# -- interaction -------------------------------------------------------------
c, w = make("Disk", [("a", 25), ("b", 25), ("c", 25), ("d", 25)], 0.0, YChartLegendPosition.Right)
w.grab()  # force paint so layout is known
cx, cy, r = w._center.x(), w._center.y(), w._radius
check("layout: pie radius > 0", r > 20, r)
QTest.mouseClick(w, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(int(cx + r / 2), int(cy + r / 2)))
check("click: bottom-right is slice b", c.selectedSlice() == 1 and len(posted) == 1, (c.selectedSlice(), len(posted)))
row, idx = w._row_rects[3]
QTest.mouseClick(w, QtCore.Qt.MouseButton.LeftButton, pos=row.center().toPoint())
check("click: legend row d", c.selectedSlice() == 3 and len(posted) == 2)
QTest.mouseClick(w, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(1, 1))
check("click: outside does nothing", len(posted) == 2)
w.setFocus()
QTest.keyClick(w, QtCore.Qt.Key.Key_Right)
check("key: right wraps to 0, no event", c.selectedSlice() == 0 and len(posted) == 2)
QTest.keyClick(w, QtCore.Qt.Key.Key_Return)
check("key: Enter activates", len(posted) == 3 and c.selectedSlice() == 0)
c.setNotify(False)
QTest.mouseClick(w, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(int(cx - r / 2), int(cy + r / 2)))
check("notify off: selects, no event", c.selectedSlice() == 2 and len(posted) == 3)
c.setNotify(True)
c.setEnabled(False)
QTest.mouseClick(w, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(int(cx + r / 2), int(cy - r / 2)))
check("disabled: no event", len(posted) == 3)
c.setEnabled(True)
c.setDonutRatio(0.6)
w.grab()
QTest.mouseClick(w, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(int(cx), int(cy)))
check("donut: hole click ignored", len(posted) == 3)
check("sizeHint sane", w.sizeHint().width() > 200 and w.minimumSizeHint().height() > 0, w.sizeHint())

from manatools.aui.backends.qt.chartpieqt import _plain_tooltip
doc = QtGui.QTextDocument()
doc.setHtml(_plain_tooltip('<b>pkg</b> & <img src="/etc/x.png">: 1'))
check("tooltip: labels shown literally", doc.toPlainText() == '<b>pkg</b> & <img src="/etc/x.png">: 1',
      doc.toPlainText())
c, w = make("dense", [(f"s{i}", 1 + i % 7) for i in range(3000)])
check("dense pie paints", not w.grab().isNull())
print("FAILED: " + ", ".join(fails) if fails else "all passed")
sys.exit(1 if fails else 0)
