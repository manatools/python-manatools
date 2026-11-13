# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Qt backend YChartBar.

A single QWidget painted with QPainter (no QtCharts dependency): optional
title, value axis with tick labels and optional gridlines, category labels,
bars (grouped or stacked, vertical or horizontal), optional value labels and
a series legend on the right or at the bottom.  The model, the axis range,
the bar geometry and the hit test come from YChartBarBase; this module only
lays out with real font metrics, paints and maps input to _bar_clicked().

Mouse: click on a bar activates it; hovering shows the bar tooltip (else the
widget help text).  Keyboard: arrows along the category axis move between
categories, the other two arrows between series; Enter/Space activate.

License: LGPLv2+

@package manatools.aui.backends.qt
'''
import logging
import math
import weakref

from PySide6 import QtWidgets, QtCore, QtGui
from ...yui_common import *
from .chartpieqt import _elide, _plain_tooltip

_GAP = 6            # pixels between labels, axis, legend and title
_ROW_PAD = 4        # extra height of a legend row over the font height
_MIN_PLOT = 48      # smallest plot side worth drawing
_NO_DATA = "No data"
_MIN_LABEL_CHARS = 6

Qt = QtCore.Qt


class _BarCanvas(QtWidgets.QWidget):
    """Paints a YChartBarQt and reports input back to it."""

    def __init__(self, owner, parent=None):
        super().__init__(parent)
        self._owner = weakref.ref(owner)
        self._plot = None       # (left, top, right, bottom, horizontal, vmin, span) of last paint
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    # -- legend metrics -----------------------------------------------------

    def _legend_rows(self, owner):
        rows = owner._legend_rows()
        if owner.legendPosition() == YChartLegendPosition.Hidden or not any(r[1] for r in rows):
            return []
        return rows

    def _cached(self, owner, name, compute):
        """Value of *compute()* cached until the data or the font changes."""
        key = (owner._version, owner.legendPosition(), self.font().key())
        cache = getattr(self, "_measure_cache", None)
        if cache is None or cache[0] != key:
            cache = self._measure_cache = (key, {})
        if name not in cache[1]:
            cache[1][name] = compute()
        return cache[1][name]

    def _widest(self, owner, name, texts):
        fm = self.fontMetrics()
        return self._cached(owner, name, lambda: max((fm.horizontalAdvance(t) for t in texts), default=0))

    def _legend_size(self, owner):
        """(row height, swatch, width of the widest row) of the series legend."""
        return self._cached(owner, "legend", lambda: self._measure_legend(owner))

    def _measure_legend(self, owner):
        fm = self.fontMetrics()
        row_h = fm.height() + _ROW_PAD
        swatch = max(8, int(fm.height() * 0.8))
        rows = self._legend_rows(owner)
        bold = QtGui.QFont(self.font())
        bold.setBold(True)              # the selected series is drawn bold
        bfm = QtGui.QFontMetrics(bold)
        widest = max((bfm.horizontalAdvance(r[1]) for r in rows), default=0)
        return row_h, swatch, 2 + swatch + _GAP + widest + 2

    # -- size ---------------------------------------------------------------

    def sizeHint(self):
        owner = self._owner()
        if owner is None:
            return QtCore.QSize(360, 240)
        fm = self.fontMetrics()
        n = max(1, owner.categoryCount())
        k = max(1, owner.seriesCount())
        per = (k if not owner.stacked() else 1) * 10 + 10
        if owner.orientation() == YChartBarOrientation.Horizontal:
            w, h = 320, max(160, n * max(per, fm.height() + 4))
        else:
            w, h = max(240, n * per) + 40, 220
        h = min(h, 600)
        w = min(w, 900)
        rows = self._legend_rows(owner)
        if rows:
            row_h, _sw, legend_w = self._legend_size(owner)
            if owner.legendPosition() == YChartLegendPosition.Bottom:
                h += _GAP + row_h * min(len(rows), 4)
            else:
                w += _GAP + min(legend_w, 240)
        if owner.label():
            h += fm.height() + _GAP
        return QtCore.QSize(w, h)

    def minimumSizeHint(self):
        fm = self.fontMetrics()
        return QtCore.QSize(_MIN_PLOT * 3, _MIN_PLOT + 2 * fm.height())

    # -- layout -------------------------------------------------------------

    def _layout(self, owner):
        """(title rect, plot area rect, legend rect) for the current size."""
        fm = self.fontMetrics()
        area = QtCore.QRectF(self.contentsRect()).adjusted(2, 2, -2, -2)
        title = QtCore.QRectF()
        if owner.label():
            h = fm.height()
            title = QtCore.QRectF(area.left(), area.top(), area.width(), h)
            area.setTop(area.top() + h + _GAP)
        legend = QtCore.QRectF()
        rows = self._legend_rows(owner)
        if rows:
            row_h, _sw, legend_w = self._legend_size(owner)
            if owner.legendPosition() == YChartLegendPosition.Right:
                w = min(legend_w, max(area.width() - 2 * _MIN_PLOT - _GAP, area.width() * 0.35))
                legend = QtCore.QRectF(area.right() - w, area.top(), w, area.height())
                area.setRight(legend.left() - _GAP)
            else:
                h = min(len(rows) * row_h, max(area.height() - _MIN_PLOT - _GAP, area.height() * 0.3))
                w = min(legend_w, area.width())
                legend = QtCore.QRectF(area.center().x() - w / 2.0, area.bottom() - h, w, h)
                area.setBottom(legend.top() - _GAP)
        return title, area, legend

    def _plot_rect(self, owner, area, tick_texts, cat_texts):
        """Plot rectangle inside *area*, leaving room for axis/category labels."""
        fm = self.fontMetrics()
        fh = fm.height()
        values = owner.showValues() and not owner.stacked()
        if owner.orientation() == YChartBarOrientation.Horizontal:
            cat_w = self._widest(owner, "categories", cat_texts)
            left = area.left() + min(cat_w, area.width() * 0.35) + _GAP
            right = area.right() - fm.horizontalAdvance(tick_texts[-1]) / 2.0 - 2
            top = area.top() + 2
            bottom = area.bottom() - fh - _GAP
        else:
            tick_w = max(fm.horizontalAdvance(t) for t in tick_texts)
            left = area.left() + tick_w + _GAP
            right = area.right() - 2
            top = area.top() + fh / 2.0 + (fh if values else 0)
            bottom = area.bottom() - fh - _GAP
        return QtCore.QRectF(QtCore.QPointF(left, top), QtCore.QPointF(right, bottom))

    # -- painting -----------------------------------------------------------

    def paintEvent(self, _event):
        owner = self._owner()
        if owner is None:
            return
        painter = QtGui.QPainter(self)
        try:
            self._paint(painter, owner)
        except Exception:
            owner._logger.exception("paint failed")
        finally:
            painter.end()

    def _paint(self, p, owner):
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        pal = self.palette()
        text = pal.color(QtGui.QPalette.ColorRole.WindowText)
        muted = pal.color(QtGui.QPalette.ColorRole.PlaceholderText)
        if not self.isEnabled():
            p.setOpacity(0.5)
        fm = self.fontMetrics()
        fh = fm.height()

        title_rect, area, legend_rect = self._layout(owner)
        if not title_rect.isNull():
            font = QtGui.QFont(self.font())
            font.setBold(True)
            p.setFont(font)
            p.setPen(text)
            p.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       _elide(p.fontMetrics(), owner.label(), title_rect.width()))
            p.setFont(self.font())

        self._paint_legend(p, owner, legend_rect, text)

        horizontal = owner.orientation() == YChartBarOrientation.Horizontal
        vmin, vmax, ticks = owner._value_axis()
        span = (vmax - vmin) or 1.0
        tick_texts = [owner._format_tick(t) for t in ticks]
        n = owner.categoryCount()
        cat_texts = [owner.categoryLabel(c) for c in range(n)]
        plot = self._plot_rect(owner, area, tick_texts, cat_texts)
        if plot.width() < 8 or plot.height() < 8:
            self._plot = None
            return
        left, top, right, bottom = plot.left(), plot.top(), plot.right(), plot.bottom()
        self._plot = (left, top, right, bottom, horizontal, vmin, span)

        def vpos(v):
            if horizontal:
                return left + (v - vmin) / span * plot.width()
            return bottom - (v - vmin) / span * plot.height()

        def upos(u):
            return (top + u * plot.height()) if horizontal else (left + u * plot.width())

        # value axis: gridlines, zero line, tick labels
        grid = QtGui.QPen(pal.color(QtGui.QPalette.ColorRole.Mid), 0.5)
        zero = QtGui.QPen(muted, 1)
        for t, label in zip(ticks, tick_texts):
            pos = vpos(t)
            if t == 0 or owner.showGrid():
                p.setPen(zero if t == 0 else grid)
                if horizontal:
                    p.drawLine(QtCore.QPointF(pos, top), QtCore.QPointF(pos, bottom))
                else:
                    p.drawLine(QtCore.QPointF(left, pos), QtCore.QPointF(right, pos))
            p.setPen(muted)
            if horizontal:
                w = fm.horizontalAdvance(label)
                p.drawText(QtCore.QRectF(pos - w / 2.0 - 1, bottom + _GAP / 2.0, w + 2, fh),
                           Qt.AlignmentFlag.AlignCenter, label)
            else:
                p.drawText(QtCore.QRectF(area.left(), pos - fh / 2.0, left - area.left() - _GAP / 2.0, fh),
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)
        p.setPen(zero)
        if horizontal:
            p.drawLine(QtCore.QPointF(left, bottom), QtCore.QPointF(right, bottom))
        else:
            p.drawLine(QtCore.QPointF(left, top), QtCore.QPointF(left, bottom))

        if n == 0 or owner.seriesCount() == 0:
            p.setPen(text)
            p.drawText(plot, Qt.AlignmentFlag.AlignCenter, _NO_DATA)
            return

        # category labels, thinned out when they would overlap
        slot = (plot.height() if horizontal else plot.width()) / n
        p.setPen(text)
        if horizontal:
            every = max(1, math.ceil(fh / slot))
            for c in range(0, n, every):
                mid = upos((c + 0.5) / n)
                p.drawText(QtCore.QRectF(area.left(), mid - fh / 2.0, left - area.left() - _GAP, fh),
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                           _elide(fm, cat_texts[c], left - area.left() - _GAP))
        else:
            longest = self._widest(owner, "categories", cat_texts)
            want = min(longest, fm.horizontalAdvance("M" * _MIN_LABEL_CHARS)) + 2 * _GAP
            every = max(1, math.ceil(want / slot))
            width = slot * every - 2 * _GAP
            last_end = -1e9
            for c in range(0, n, every):
                label = _elide(fm, cat_texts[c], width)
                lw = fm.horizontalAdvance(label)
                x = upos((c + 0.5) / n) - lw / 2.0
                x = max(area.left(), min(x, area.right() - lw))    # keep inside the widget
                if x < last_end + _GAP:
                    continue                # pushed onto its neighbour by the edge
                last_end = x + lw
                p.drawText(QtCore.QRectF(x, bottom + _GAP / 2.0, lw + 1, fh),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)

        # bars; bars thinner than a pixel are merged per pixel line and color
        # (overlapping extents only) so dense charts draw at most a few rects
        # per pixel instead of one per bar
        selected = (owner.selectedCategory(), owner.selectedSeries())
        sel_rect = None
        values = []
        thin = {}           # (pixel, color) -> [[lo, hi], ...] along the value axis
        p.setPen(Qt.PenStyle.NoPen)
        for c, s, u0, u1, v0, v1, color in owner._bar_geometry():
            a, b = upos(u0), upos(u1)
            q0, q1 = vpos(v0), vpos(v1)
            lo, hi = min(q0, q1), max(q0, q1)
            if horizontal:
                rect = QtCore.QRectF(lo, a, max(hi - lo, 1.0), max(b - a, 1.0))
            else:
                rect = QtCore.QRectF(a, lo, max(b - a, 1.0), max(hi - lo, 1.0))
            if (c, s) == selected:
                sel_rect = rect
            if b - a < 1.0:
                spans = thin.setdefault((int(a), color), [])
                if spans and lo <= spans[-1][1] + 1.0 and hi >= spans[-1][0] - 1.0:
                    spans[-1][0] = min(spans[-1][0], lo)
                    spans[-1][1] = max(spans[-1][1], hi)
                else:
                    spans.append([lo, hi])
                continue
            p.setBrush(QtGui.QColor(color))
            p.drawRect(rect)
            if owner.showValues() and b - a >= 3.0:     # no room for labels on thinner bars
                values.append((c, s, rect, v1 >= v0))
        for (pixel, color), spans in thin.items():
            p.setBrush(QtGui.QColor(color))
            for lo, hi in spans:
                if horizontal:
                    p.drawRect(QtCore.QRectF(lo, pixel, max(hi - lo, 1.0), 1.0))
                else:
                    p.drawRect(QtCore.QRectF(pixel, lo, 1.0, max(hi - lo, 1.0)))
        if sel_rect is not None:
            p.setPen(QtGui.QPen(text, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(sel_rect)

        # value labels: inside the segment when stacked, else past the bar end
        for c, s, rect, up in values:
            label = owner._value_text(c, s)
            tw = fm.horizontalAdvance(label)
            inside = False
            if owner.stacked():
                if (rect.width() if horizontal else rect.height()) < (tw + 4 if horizontal else fh):
                    continue
                if rect.width() < tw + 2:
                    continue
                box = rect
                inside = True
            elif horizontal:
                if up and rect.right() + 2 + tw <= right:
                    box = QtCore.QRectF(rect.right() + 2, rect.top(), tw + 2, rect.height())
                elif not up and rect.left() - 2 - tw >= left:
                    box = QtCore.QRectF(rect.left() - 4 - tw, rect.top(), tw + 2, rect.height())
                else:
                    box, inside = rect.adjusted(2, 0, -2, 0), True
            else:
                if up and rect.top() - fh >= area.top():
                    box = QtCore.QRectF(rect.center().x() - tw / 2.0 - 1, rect.top() - fh, tw + 2, fh)
                elif not up and rect.bottom() + fh <= bottom:
                    box = QtCore.QRectF(rect.center().x() - tw / 2.0 - 1, rect.bottom(), tw + 2, fh)
                else:
                    box, inside = rect, True
            align = Qt.AlignmentFlag.AlignCenter
            if inside and not owner.stacked():
                if horizontal:
                    align = (Qt.AlignmentFlag.AlignRight if up else Qt.AlignmentFlag.AlignLeft) | Qt.AlignmentFlag.AlignVCenter
                else:
                    align = Qt.AlignmentFlag.AlignHCenter | (Qt.AlignmentFlag.AlignTop if up else Qt.AlignmentFlag.AlignBottom)
            if inside:
                self._outlined_text(p, box, align, label)
            else:
                p.setPen(text)
                p.drawText(box, align, label)

        if self.hasFocus():
            opt = QtWidgets.QStyleOptionFocusRect()
            opt.initFrom(self)
            self.style().drawPrimitive(QtWidgets.QStyle.PrimitiveElement.PE_FrameFocusRect, opt, p, self)

    def _outlined_text(self, p, box, align, label):
        """White text with a dark halo, readable on any bar color."""
        p.setPen(QtGui.QColor(0, 0, 0, 110))
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            p.drawText(box.translated(dx, dy), align, label)
        p.setPen(QtGui.QColor("white"))
        p.drawText(box, align, label)

    def _paint_legend(self, p, owner, rect, text):
        if rect.isNull() or rect.height() <= 0:
            return
        fm = self.fontMetrics()
        row_h, swatch, _w = self._legend_size(owner)
        rows = self._legend_rows(owner)
        fit = max(0, int(rect.height() // row_h))
        hidden = 0
        if fit < len(rows):
            hidden = len(rows) - max(fit - 1, 0)
            rows = rows[:max(fit - 1, 0)]
        y = rect.top()
        left = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        for s, name, color in rows:
            row = QtCore.QRectF(rect.left(), y, rect.width(), row_h)
            sw = QtCore.QRectF(row.left() + 2, row.center().y() - swatch / 2.0, swatch, swatch)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QColor(color))
            p.drawRoundedRect(sw, 2, 2)
            font = QtGui.QFont(self.font())
            font.setBold(s == owner.selectedSeries())
            p.setFont(font)
            p.setPen(text)
            x = sw.right() + _GAP
            p.drawText(QtCore.QRectF(x, y, row.right() - x, row_h), left,
                       _elide(p.fontMetrics(), name, row.right() - x))
            p.setFont(self.font())
            y += row_h
        if hidden and fit > 0:
            p.setPen(text)
            p.drawText(QtCore.QRectF(rect.left() + 2, y, rect.width(), row_h), left, f"… +{hidden}")

    # -- input --------------------------------------------------------------

    def _bar_at_pos(self, owner, pos):
        if self._plot is None:
            return -1, -1
        left, top, right, bottom, horizontal, vmin, span = self._plot
        if not (left <= pos.x() <= right and top <= pos.y() <= bottom):
            return -1, -1
        length = max(1.0, (bottom - top) if horizontal else (right - left))
        if horizontal:
            u = (pos.y() - top) / length
            v = vmin + (pos.x() - left) / max(1.0, right - left) * span
        else:
            u = (pos.x() - left) / length
            v = vmin + (bottom - pos.y()) / max(1.0, bottom - top) * span
        return owner._bar_at(u, v, 1.0 / length)       # one pixel of tolerance

    def mousePressEvent(self, event):
        owner = self._owner()
        if owner is None or event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        c, s = self._bar_at_pos(owner, event.position())
        if c >= 0:
            owner._bar_clicked(c, s)
        event.accept()

    def mouseMoveEvent(self, event):
        owner = self._owner()
        if owner is not None:
            over = self._bar_at_pos(owner, event.position())[0] >= 0
            self.setCursor(Qt.CursorShape.PointingHandCursor if over else Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event):
        owner = self._owner()
        if owner is None or owner.categoryCount() == 0 or owner.seriesCount() == 0:
            return super().keyPressEvent(event)
        n, k = owner.categoryCount(), owner.seriesCount()
        c, s = owner.selectedCategory(), owner.selectedSeries()
        key = event.key()
        Key = Qt.Key
        if owner.orientation() == YChartBarOrientation.Horizontal:
            cat_next, cat_prev, ser_next, ser_prev = Key.Key_Down, Key.Key_Up, Key.Key_Right, Key.Key_Left
        else:
            cat_next, cat_prev, ser_next, ser_prev = Key.Key_Right, Key.Key_Left, Key.Key_Up, Key.Key_Down
        if key in (Key.Key_Return, Key.Key_Enter, Key.Key_Space):
            if c < 0:
                return super().keyPressEvent(event)
            owner._bar_clicked(c, s)
        elif key in (cat_next, cat_prev, ser_next, ser_prev):
            if c < 0:
                c, s = 0, 0
            elif key == cat_next:
                c = min(n - 1, c + 1)
            elif key == cat_prev:
                c = max(0, c - 1)
            elif key == ser_next:
                s = min(k - 1, s + 1)
            else:
                s = max(0, s - 1)
            owner.setSelectedBar(c, s)
        else:
            return super().keyPressEvent(event)
        event.accept()

    def event(self, event):
        if event.type() == QtCore.QEvent.Type.ToolTip:
            owner = self._owner()
            tip = ""
            if owner is not None:
                c, s = self._bar_at_pos(owner, QtCore.QPointF(event.pos()))
                # Bar labels are data: shown literally.  The help text is
                # passed as is, like every other Qt widget's tooltip.
                tip = _plain_tooltip(owner._bar_tooltip(c, s)) if c >= 0 else owner.helpText()
            if tip:
                QtWidgets.QToolTip.showText(event.globalPos(), tip, self)
            else:
                QtWidgets.QToolTip.hideText()
                event.ignore()
            return True
        return super().event(event)


class YChartBarQt(YChartBarBase):
    """Bar chart painted with QPainter."""

    def __init__(self, parent=None, label: str = ""):
        # Attributes first: addChild() on the parent may build us immediately.
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        super().__init__(parent, label)

    def _create_backend_widget(self):
        canvas = _BarCanvas(self)
        try:
            expand = QtWidgets.QSizePolicy.Policy.Expanding
            preferred = QtWidgets.QSizePolicy.Policy.Preferred
            canvas.setSizePolicy(
                expand if (self.stretchable(YUIDimension.YD_HORIZ) or self.weight(YUIDimension.YD_HORIZ)) else preferred,
                expand if (self.stretchable(YUIDimension.YD_VERT) or self.weight(YUIDimension.YD_VERT)) else preferred)
            canvas.setEnabled(bool(self._enabled))
            canvas.setVisible(self.visible())
            canvas.setAccessibleName(self._label or "Bar chart")
        except Exception:
            self._logger.exception("Failed to apply initial widget state")
        self._backend_widget = canvas
        self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())

    # -- backend hooks ------------------------------------------------------

    def _apply_chart(self):
        canvas = getattr(self, "_backend_widget", None)
        if canvas is None:
            return
        try:
            canvas.setAccessibleName(self._label or "Bar chart")
            canvas.updateGeometry()
            canvas.update()
        except Exception:
            self._logger.exception("Failed to redraw chart")

    # -- common widget API --------------------------------------------------

    def _set_backend_enabled(self, enabled):
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.setEnabled(bool(enabled))
        except Exception:
            self._logger.exception("Failed to set enabled state")

    def setVisible(self, visible=True):
        super().setVisible(visible)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.setVisible(visible)
        except Exception:
            self._logger.exception("setVisible failed")

    def setHelpText(self, help_text: str):
        # Shown by _BarCanvas.event() when the pointer is not over a bar.
        super().setHelpText(help_text)
