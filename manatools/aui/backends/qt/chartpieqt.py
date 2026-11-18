# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Qt backend YChartPie.

A single QWidget painted with QPainter (no QtCharts dependency): optional
title, pie or donut, legend on the right or at the bottom.  The model, the
geometry and the hit test come from YChartPieBase; this module only lays
out, paints and maps mouse/keyboard input to _slice_clicked().

Mouse: click on a slice or legend row activates it; hovering shows the slice
tooltip (else the widget help text).  Keyboard: arrows move the selection,
Enter/Space activate the selected slice.

License: LGPLv2+

@package manatools.aui.backends.qt
'''
import html
import logging
import math
import weakref

from PySide6 import QtWidgets, QtCore, QtGui
from ...yui_common import *

_GAP = 8            # pixels between pie, legend and title
_ROW_PAD = 4        # extra height of a legend row over the font height
_MIN_PIE = 64       # smallest pie diameter worth drawing
_NO_DATA = "No data"


def _plain_tooltip(text):
    """Tooltip markup showing *text* literally: QToolTip would otherwise
    render chart labels that look like HTML as rich text."""
    return "<qt>" + html.escape(text, quote=False) + "</qt>"


def _elide(fm, text, width):
    """*text* elided to *width*; QFontMetrics.elidedText() alone also elides
    text whose advance is exactly *width*."""
    width = int(width)
    if fm.horizontalAdvance(text) <= width:
        return text
    return fm.elidedText(text, QtCore.Qt.TextElideMode.ElideRight, width)


class _PieCanvas(QtWidgets.QWidget):
    """Paints a YChartPieQt and reports input back to it."""

    def __init__(self, owner, parent=None):
        super().__init__(parent)
        self._owner = weakref.ref(owner)
        # Layout of the last paint, used for hit testing.
        self._center = QtCore.QPointF()
        self._radius = 0.0
        self._row_rects = []        # [(QRectF, slice index)]
        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover, True)

    # -- size ---------------------------------------------------------------

    def _legend_metrics(self, owner):
        """(row height, swatch size, value col width, pct col width, label width).

        Measuring every label is O(slices): cached until the data, the
        percent column or the font changes.
        """
        key = (owner._version, owner.showPercent(), self.font().key())
        cached = getattr(self, "_metrics_cache", None)
        if cached is not None and cached[0] == key:
            return cached[1]
        fm = self.fontMetrics()
        row_h = fm.height() + _ROW_PAD
        swatch = max(8, int(fm.height() * 0.8))
        rows = owner._legend_rows()
        value_w = max((fm.horizontalAdvance(r[2]) for r in rows), default=0)
        pct_w = fm.horizontalAdvance("100.0%") if owner.showPercent() else 0
        label_w = max((fm.horizontalAdvance(r[1]) for r in rows), default=0)
        metrics = (row_h, swatch, value_w, pct_w, label_w)
        self._metrics_cache = (key, metrics)
        return metrics

    def _legend_width(self, owner, label_w=None):
        row_h, swatch, value_w, pct_w, full_label_w = self._legend_metrics(owner)
        label_w = full_label_w if label_w is None else label_w
        # +2 for the swatch inset, +2 right margin.
        w = 2 + swatch + _GAP + label_w + _GAP + value_w + 2
        if pct_w:
            w += _GAP + pct_w
        return w

    def _title_height(self, owner):
        return (self.fontMetrics().height() + _GAP) if owner.label() else 0

    def sizeHint(self):
        owner = self._owner()
        if owner is None:
            return QtCore.QSize(320, 240)
        pie = 200
        title_h = self._title_height(owner)
        pos = owner.legendPosition()
        if pos == YChartLegendPosition.Hidden or owner.sliceCount() == 0:
            return QtCore.QSize(pie, pie + title_h)
        row_h = self._legend_metrics(owner)[0]
        legend_w = min(self._legend_width(owner), 320)
        legend_h = min(owner.sliceCount(), 12) * row_h
        if pos == YChartLegendPosition.Bottom:
            return QtCore.QSize(max(pie, legend_w), pie + _GAP + legend_h + title_h)
        return QtCore.QSize(pie + _GAP + legend_w, max(pie, legend_h) + title_h)

    def minimumSizeHint(self):
        owner = self._owner()
        title_h = self._title_height(owner) if owner is not None else 0
        return QtCore.QSize(_MIN_PIE * 2, _MIN_PIE + title_h)

    # -- layout -------------------------------------------------------------

    def _layout(self, owner):
        """(title rect, pie rect (square), legend rect) for the current size."""
        area = QtCore.QRectF(self.contentsRect()).adjusted(2, 2, -2, -2)
        title = QtCore.QRectF()
        if owner.label():
            h = self.fontMetrics().height()
            title = QtCore.QRectF(area.left(), area.top(), area.width(), h)
            area.setTop(area.top() + h + _GAP)

        legend = QtCore.QRectF()
        pos = owner.legendPosition()
        if pos != YChartLegendPosition.Hidden and owner.sliceCount() > 0:
            if pos == YChartLegendPosition.Right:
                w = min(self._legend_width(owner), max(area.width() - _MIN_PIE - _GAP, area.width() * 0.5))
                legend = QtCore.QRectF(area.right() - w, area.top(), w, area.height())
                area.setRight(legend.left() - _GAP)
            else:
                row_h = self._legend_metrics(owner)[0]
                h = min(owner.sliceCount() * row_h, max(area.height() - _MIN_PIE - _GAP, area.height() * 0.4))
                w = min(self._legend_width(owner), area.width())
                legend = QtCore.QRectF(area.center().x() - w / 2.0, area.bottom() - h, w, h)
                area.setBottom(legend.top() - _GAP)

        side = max(0.0, min(area.width(), area.height()))
        pie = QtCore.QRectF(0, 0, side, side)
        pie.moveCenter(area.center())
        return title, pie, legend

    # -- painting -----------------------------------------------------------

    @staticmethod
    def _sector_path(rect, inner_rect, start, sweep):
        """Path of a slice; angles as in YChartPieBase (0 = 12 o'clock, clockwise)."""
        path = QtGui.QPainterPath()
        path.setFillRule(QtCore.Qt.FillRule.OddEvenFill)
        if sweep >= 359.999:
            path.addEllipse(rect)
            if inner_rect is not None:
                path.addEllipse(inner_rect)
            return path
        qt_start = 90.0 - start          # Qt: 0 = 3 o'clock, counter-clockwise
        if inner_rect is None:
            path.moveTo(rect.center())
            path.arcTo(rect, qt_start, -sweep)
        else:
            path.arcMoveTo(rect, qt_start)
            path.arcTo(rect, qt_start, -sweep)
            path.arcTo(inner_rect, qt_start - sweep, sweep)
        path.closeSubpath()
        return path

    def _fill_sector(self, p, rect, inner_rect, sector, pen):
        start, sweep, color = sector
        p.setPen(pen if pen is not None else QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(color))
        p.drawPath(self._sector_path(rect, inner_rect, start, sweep))

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
        text_color = pal.color(QtGui.QPalette.ColorRole.WindowText)
        if not self.isEnabled():
            p.setOpacity(0.5)

        title_rect, pie_rect, legend_rect = self._layout(owner)

        if not title_rect.isNull():
            font = QtGui.QFont(self.font())
            font.setBold(True)
            p.setFont(font)
            p.setPen(text_color)
            p.drawText(title_rect, QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                       _elide(p.fontMetrics(), owner.label(), title_rect.width()))
            p.setFont(self.font())

        self._center = pie_rect.center()
        self._radius = pie_rect.width() / 2.0
        ratio = owner.donutRatio()
        inner_rect = None
        if ratio > 0 and pie_rect.width() > 0:
            r_in = self._radius * ratio
            inner_rect = QtCore.QRectF(0, 0, 2 * r_in, 2 * r_in)
            inner_rect.moveCenter(self._center)

        geom = owner._geometry()
        if pie_rect.width() >= 4:
            if not geom:
                if inner_rect is None:
                    r_in = self._radius * 0.6
                    inner_rect = QtCore.QRectF(0, 0, 2 * r_in, 2 * r_in)
                    inner_rect.moveCenter(self._center)
                p.setPen(QtCore.Qt.PenStyle.NoPen)
                p.setBrush(pal.color(QtGui.QPalette.ColorRole.Mid))
                p.drawPath(self._sector_path(pie_rect, inner_rect, 0, 360))
                p.setPen(text_color)
                p.drawText(pie_rect, QtCore.Qt.AlignmentFlag.AlignCenter, _NO_DATA)
            else:
                border = QtGui.QPen(pal.color(QtGui.QPalette.ColorRole.Base), 1)
                selected_path = None
                selected = owner.selectedSlice()
                # Slices thinner than a pixel along the rim are invisible on
                # their own: draw each run of them as one wedge (color of its
                # first slice).  Hit testing still uses the real slices.
                deg_px = 360.0 / max(1e-9, 2 * math.pi * self._radius)
                run = None          # [start, sweep, color]
                for index, start, sweep, color in geom:
                    if index == selected:
                        selected_path = self._sector_path(pie_rect, inner_rect, start, sweep)
                    if sweep < deg_px:
                        if run is None:
                            run = [start, sweep, color]
                        else:
                            run[1] += sweep
                        if run[1] < deg_px:
                            continue
                        start, sweep, color = run
                    elif run is not None:
                        self._fill_sector(p, pie_rect, inner_rect, run, None)
                    run = None
                    # Separators only where they leave some slice visible.
                    pen = border if sweep >= 3 * deg_px else None
                    self._fill_sector(p, pie_rect, inner_rect, (start, sweep, color), pen)
                if run is not None:
                    self._fill_sector(p, pie_rect, inner_rect, run, None)
                if selected_path is not None:
                    p.setPen(QtGui.QPen(text_color, 2.5))
                    p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
                    p.drawPath(selected_path)
                if inner_rect is not None and owner.centerText():
                    p.setPen(text_color)
                    p.drawText(inner_rect, QtCore.Qt.AlignmentFlag.AlignCenter,
                               _elide(self.fontMetrics(), owner.centerText(), inner_rect.width() * 0.9))

        self._paint_legend(p, owner, legend_rect, text_color)

        if self.hasFocus():
            opt = QtWidgets.QStyleOptionFocusRect()
            opt.initFrom(self)
            self.style().drawPrimitive(QtWidgets.QStyle.PrimitiveElement.PE_FrameFocusRect, opt, p, self)

    def _paint_legend(self, p, owner, rect, text_color):
        self._row_rects = []
        if rect.isNull() or rect.height() <= 0:
            return
        row_h, swatch, value_w, pct_w, _label_w = self._legend_metrics(owner)
        fm = self.fontMetrics()
        rows = owner._legend_rows()
        fit = max(0, int(rect.height() // row_h))
        hidden = 0
        if fit < len(rows):
            hidden = len(rows) - max(fit - 1, 0)
            rows = rows[:max(fit - 1, 0)]
        label_w = rect.width() - 2 - swatch - _GAP - value_w - _GAP - 2 - ((_GAP + pct_w) if pct_w else 0)
        y = rect.top()
        right = QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        left = QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        highlight = self.palette().color(QtGui.QPalette.ColorRole.Highlight)
        highlight.setAlpha(60)
        for index, label, value_text, pct_text, color in rows:
            row = QtCore.QRectF(rect.left(), y, rect.width(), row_h)
            self._row_rects.append((row, index))
            if index == owner.selectedSlice():
                p.setPen(QtCore.Qt.PenStyle.NoPen)
                p.setBrush(highlight)
                p.drawRoundedRect(row, 3, 3)
            sw = QtCore.QRectF(row.left() + 2, row.center().y() - swatch / 2.0, swatch, swatch)
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QColor(color))
            p.drawRoundedRect(sw, 2, 2)
            p.setPen(text_color)
            x = sw.right() + _GAP
            if label_w > 0:
                p.drawText(QtCore.QRectF(x, y, label_w, row_h), left,
                           _elide(fm, label, label_w))
                x += label_w + _GAP
            p.drawText(QtCore.QRectF(x, y, value_w, row_h), right, value_text)
            x += value_w + _GAP
            if pct_w:
                p.drawText(QtCore.QRectF(x, y, pct_w, row_h), right, pct_text)
            y += row_h
        if hidden and fit > 0:
            p.setPen(text_color)
            p.drawText(QtCore.QRectF(rect.left() + 2, y, rect.width(), row_h), left,
                       f"… +{hidden}")

    # -- input --------------------------------------------------------------

    def _index_at(self, owner, pos) -> int:
        for row, index in self._row_rects:
            if row.contains(pos):
                return index
        d = pos - self._center
        return owner._slice_at(d.x(), d.y(), self._radius)

    def mousePressEvent(self, event):
        owner = self._owner()
        if owner is None or event.button() != QtCore.Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        index = self._index_at(owner, event.position())
        if index >= 0:
            owner._slice_clicked(index)
        event.accept()

    def mouseMoveEvent(self, event):
        owner = self._owner()
        if owner is not None:
            over = self._index_at(owner, event.position()) >= 0
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor if over
                           else QtCore.Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event):
        owner = self._owner()
        count = owner.sliceCount() if owner is not None else 0
        if count == 0:
            return super().keyPressEvent(event)
        key = event.key()
        Key = QtCore.Qt.Key
        current = owner.selectedSlice()
        if key in (Key.Key_Right, Key.Key_Down):
            owner.setSelectedSlice((current + 1) % count)
        elif key in (Key.Key_Left, Key.Key_Up):
            owner.setSelectedSlice((current - 1) % count if current >= 0 else count - 1)
        elif key in (Key.Key_Return, Key.Key_Enter, Key.Key_Space) and current >= 0:
            owner._slice_clicked(current)
        else:
            return super().keyPressEvent(event)
        event.accept()

    def event(self, event):
        if event.type() == QtCore.QEvent.Type.ToolTip:
            owner = self._owner()
            text = ""
            if owner is not None:
                index = self._index_at(owner, QtCore.QPointF(event.pos()))
                # Slice labels are data: shown literally.  The help text is
                # passed as is, like every other Qt widget's tooltip.
                text = _plain_tooltip(owner._slice_tooltip(index)) if index >= 0 else owner.helpText()
            if text:
                QtWidgets.QToolTip.showText(event.globalPos(), text, self)
            else:
                QtWidgets.QToolTip.hideText()
                event.ignore()
            return True
        return super().event(event)


class YChartPieQt(YChartPieBase):
    """Pie / donut chart painted with QPainter."""

    def __init__(self, parent=None, label: str = ""):
        # Attributes first: addChild() on the parent may build us immediately.
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        super().__init__(parent, label)

    def _create_backend_widget(self):
        canvas = _PieCanvas(self)
        try:
            expand = QtWidgets.QSizePolicy.Policy.Expanding
            preferred = QtWidgets.QSizePolicy.Policy.Preferred
            canvas.setSizePolicy(
                expand if (self.stretchable(YUIDimension.YD_HORIZ) or self.weight(YUIDimension.YD_HORIZ)) else preferred,
                expand if (self.stretchable(YUIDimension.YD_VERT) or self.weight(YUIDimension.YD_VERT)) else preferred)
            canvas.setEnabled(bool(self._enabled))
            canvas.setVisible(self.visible())
            canvas.setAccessibleName(self._label or "Pie chart")
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
            canvas.setAccessibleName(self._label or "Pie chart")
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
        # Shown by _PieCanvas.event() when the pointer is not over a slice.
        super().setHelpText(help_text)
