# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Qt backend YChartGauge.

A single QWidget painted with QPainter (no QtCharts dependency): optional
title, the dial (track, band ring, value arc, ticks with labels, target
marker, optional needle, value text and subtitle) and a legend of the
labelled bands on the right or at the bottom.  Angles, ticks, colors and
the hit test come from YChartGaugeBase; this module only lays out, paints
and maps mouse/keyboard input to _gauge_clicked().

Mouse: a click on the dial activates it; hovering the dial shows the value
tooltip (else the widget help text).  Keyboard: Enter/Space activate.

License: LGPLv2+

@package manatools.aui.backends.qt
'''
import logging
import math
import weakref

from PySide6 import QtWidgets, QtCore, QtGui
from ...yui_common import *
from .chartpieqt import _elide, _plain_tooltip

_GAP = 8            # pixels between dial, legend and title
_ROW_PAD = 4        # extra height of a legend row over the font height
_MIN_DIAL = 48      # smallest dial radius worth laying out for
# Ring radii as fractions of the dial radius.
_BAND_IN = 0.94
_TRACK_OUT = 0.90
_TRACK_IN = 0.70


def _ring_path(center, r_out, r_in, a0, a1):
    """Annular sector from *a0* to *a1* (degrees, 0 = 12 o'clock, clockwise)."""
    outer = QtCore.QRectF(center.x() - r_out, center.y() - r_out, 2 * r_out, 2 * r_out)
    inner = QtCore.QRectF(center.x() - r_in, center.y() - r_in, 2 * r_in, 2 * r_in)
    qt_start = 90.0 - a0           # Qt: 0 = 3 o'clock, counter-clockwise
    sweep = a1 - a0
    path = QtGui.QPainterPath()
    path.arcMoveTo(outer, qt_start)
    path.arcTo(outer, qt_start, -sweep)
    path.arcTo(inner, qt_start - sweep, sweep)
    path.closeSubpath()
    return path


def _polar(center, angle, radius):
    a = math.radians(angle)
    return QtCore.QPointF(center.x() + radius * math.sin(a), center.y() - radius * math.cos(a))


class _GaugeCanvas(QtWidgets.QWidget):
    """Paints a YChartGaugeQt and reports input back to it."""

    def __init__(self, owner, parent=None):
        super().__init__(parent)
        self._owner = weakref.ref(owner)
        # Layout of the last paint, used for hit testing.
        self._center = QtCore.QPointF()
        self._radius = 0.0
        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover, True)

    # -- fonts and sizes ----------------------------------------------------

    def _tick_font(self):
        font = QtGui.QFont(self.font())
        font.setPointSizeF(max(6.0, font.pointSizeF() * 0.85))
        return font

    def _label_margins(self, owner):
        """(horizontal, vertical) room for tick labels around the dial."""
        if not owner.showTicks():
            return 2.0, 2.0
        fm = QtGui.QFontMetrics(self._tick_font())
        w = max((fm.horizontalAdvance(t) for _, _, t in owner._ticks()), default=0)
        return w + 6.0, fm.height() + 2.0

    def _legend_metrics(self, owner):
        """(rows, row height, swatch, label width, range width)."""
        fm = self.fontMetrics()
        rows = owner._legend_rows()
        row_h = fm.height() + _ROW_PAD
        swatch = max(8, int(fm.height() * 0.8))
        label_w = max((fm.horizontalAdvance(r[1]) for r in rows), default=0)
        range_w = max((fm.horizontalAdvance(r[2]) for r in rows), default=0)
        return rows, row_h, swatch, label_w, range_w

    def _legend_width(self, owner):
        _rows, _row_h, swatch, label_w, range_w = self._legend_metrics(owner)
        return 2 + swatch + _GAP + label_w + _GAP + range_w + 2

    def _has_legend(self, owner):
        return owner.legendPosition() != YChartLegendPosition.Hidden and bool(owner._legend_rows())

    def _title_height(self, owner):
        return (self.fontMetrics().height() + _GAP) if owner.label() else 0

    def _dial_size(self, owner, radius):
        mx, my = self._label_margins(owner)
        below = max(owner._dial_extent(), 0.12)
        if owner._text_placement() == "below":
            below = max(below, 0.44)
        return QtCore.QSize(int(2 * (radius + mx)), int(radius * (1 + below) + 2 * my))

    def sizeHint(self):
        owner = self._owner()
        if owner is None:
            return QtCore.QSize(240, 200)
        dial = self._dial_size(owner, 100)
        title_h = self._title_height(owner)
        if not self._has_legend(owner):
            return QtCore.QSize(dial.width(), dial.height() + title_h)
        rows, row_h = self._legend_metrics(owner)[:2]
        legend_w = min(self._legend_width(owner), 320)
        legend_h = min(len(rows), 8) * row_h
        if owner.legendPosition() == YChartLegendPosition.Bottom:
            return QtCore.QSize(max(dial.width(), legend_w), dial.height() + _GAP + legend_h + title_h)
        return QtCore.QSize(dial.width() + _GAP + legend_w, max(dial.height(), legend_h) + title_h)

    def minimumSizeHint(self):
        owner = self._owner()
        if owner is None:
            return QtCore.QSize(120, 80)
        dial = self._dial_size(owner, _MIN_DIAL)
        return QtCore.QSize(dial.width(), dial.height() + self._title_height(owner))

    # -- layout -------------------------------------------------------------

    def _layout(self, owner):
        """(title rect, dial rect, legend rect) for the current size."""
        area = QtCore.QRectF(self.contentsRect()).adjusted(2, 2, -2, -2)
        title = QtCore.QRectF()
        if owner.label():
            h = self.fontMetrics().height()
            title = QtCore.QRectF(area.left(), area.top(), area.width(), h)
            area.setTop(area.top() + h + _GAP)
        legend = QtCore.QRectF()
        if self._has_legend(owner):
            rows, row_h = self._legend_metrics(owner)[:2]
            min_dial = self._dial_size(owner, _MIN_DIAL)
            if owner.legendPosition() == YChartLegendPosition.Right:
                w = min(self._legend_width(owner), max(area.width() - min_dial.width() - _GAP, area.width() * 0.4))
                legend = QtCore.QRectF(area.right() - w, area.top(), w, area.height())
                area.setRight(legend.left() - _GAP)
                legend.setHeight(min(legend.height(), len(rows) * row_h))
                legend.moveTop(area.center().y() - legend.height() / 2.0)
            else:
                h = min(len(rows) * row_h, max(area.height() - min_dial.height() - _GAP, area.height() * 0.4))
                w = min(self._legend_width(owner), area.width())
                legend = QtCore.QRectF(area.center().x() - w / 2.0, area.bottom() - h, w, h)
                area.setBottom(legend.top() - _GAP)
        return title, area, legend

    def _fit_dial(self, owner, rect):
        """(center, radius) of the dial inside *rect*, label margins kept."""
        mx, my = self._label_margins(owner)
        w, h = max(0.0, rect.width() - 2 * mx), max(0.0, rect.height() - 2 * my)
        below = None
        if owner._text_placement() == "below":
            # Hub, value text (about 0.34 r) and the subtitle line under the center.
            below = 0.1 + (0.34 if owner.showValue() else 0.0)
            if owner.subtitle():
                h = max(0.0, h - self.fontMetrics().height())
        cx, cy, r = owner._dial_fit(w, h, below)
        return QtCore.QPointF(rect.left() + mx + cx, rect.top() + my + cy), r

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
        text_color = pal.color(QtGui.QPalette.ColorRole.WindowText)
        dim_color = QtGui.QColor(text_color)
        dim_color.setAlphaF(0.7)
        if not self.isEnabled():
            p.setOpacity(0.5)

        title_rect, dial_rect, legend_rect = self._layout(owner)
        if not title_rect.isNull():
            font = QtGui.QFont(self.font())
            font.setBold(True)
            p.setFont(font)
            p.setPen(text_color)
            p.drawText(title_rect, QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                       _elide(p.fontMetrics(), owner.label(), title_rect.width()))
            p.setFont(self.font())

        center, r = self._fit_dial(owner, dial_rect)
        self._center, self._radius = center, r
        if r >= 8:
            self._paint_dial(p, owner, center, r, text_color, dim_color)
        self._paint_legend(p, owner, legend_rect, text_color, dim_color)

        if self.hasFocus():
            opt = QtWidgets.QStyleOptionFocusRect()
            opt.initFrom(self)
            self.style().drawPrimitive(QtWidgets.QStyle.PrimitiveElement.PE_FrameFocusRect, opt, p, self)

    def _paint_dial(self, p, owner, c, r, text_color, dim_color):
        half = owner.sweepAngle() / 2.0
        deg_px = 360.0 / max(1e-9, 2 * math.pi * r)     # one pixel along the rim
        track = QtGui.QColor(self.palette().color(QtGui.QPalette.ColorRole.Mid))
        track.setAlphaF(0.45)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawPath(_ring_path(c, r * _TRACK_OUT, r * _TRACK_IN, -half, half))
        for _i, a0, a1, color in owner._band_arcs():
            if a1 - a0 >= deg_px * 0.25:
                p.setBrush(QtGui.QColor(color))
                p.drawPath(_ring_path(c, r, r * _BAND_IN, a0, a1))
        a0, a1, color = owner._value_arc()
        if a1 - a0 >= deg_px * 0.25:
            p.setBrush(QtGui.QColor(color))
            p.drawPath(_ring_path(c, r * _TRACK_OUT, r * _TRACK_IN, a0, a1))

        if owner.showTicks():
            font = self._tick_font()
            p.setFont(font)
            fm = QtGui.QFontMetrics(font)
            p.setPen(QtGui.QPen(dim_color, 1))
            for _v, angle, text in owner._ticks():
                p.drawLine(_polar(c, angle, r * _TRACK_OUT), _polar(c, angle, r))
                # Label box pushed outward from the rim by half its size.
                pt = _polar(c, angle, r + 3)
                w, h = fm.horizontalAdvance(text) + 1, fm.height()
                a = math.radians(angle)
                x = pt.x() + math.sin(a) * w / 2.0 - w / 2.0
                y = pt.y() - math.cos(a) * h / 2.0 - h / 2.0
                p.drawText(QtCore.QRectF(x, y, w, h), QtCore.Qt.AlignmentFlag.AlignCenter, text)
            p.setFont(self.font())

        target = owner._target_angle()
        if target is not None:
            pen = QtGui.QPen(text_color, max(2.0, r * 0.03))
            pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(_polar(c, target, r * _TRACK_IN - 4), _polar(c, target, r + 2))

        if owner.showNeedle():
            angle = owner._angle_of(owner.value())
            hub = max(3.0, r * 0.06)
            needle = QtGui.QPolygonF([_polar(c, angle, r * _TRACK_OUT - 2),
                                      _polar(c, angle + 90, hub * 0.7),
                                      _polar(c, angle + 180, hub * 1.4),
                                      _polar(c, angle - 90, hub * 0.7)])
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(text_color)
            p.drawPolygon(needle)
            p.drawEllipse(c, hub, hub)

        self._paint_text(p, owner, c, r, text_color, dim_color)

    def _paint_text(self, p, owner, c, r, text_color, dim_color):
        value = owner._value_text() if owner.showValue() else ""
        sub = owner.subtitle()
        if not value and not sub:
            return
        room = 2 * r * _TRACK_IN * 0.85
        vfont = QtGui.QFont(self.font())
        vfont.setBold(True)
        vfont.setPixelSize(max(10, int(r * 0.28)))
        if value:
            vfm = QtGui.QFontMetrics(vfont)
            adv = vfm.horizontalAdvance(value)
            if adv > room:
                vfont.setPixelSize(max(10, int(vfont.pixelSize() * room / adv)))
        vh = QtGui.QFontMetrics(vfont).height() if value else 0
        sfm = self.fontMetrics()
        sh = sfm.height() if sub else 0
        place = owner._text_placement()
        if place == "below":
            top = c.y() + max(3.0, r * 0.06) * 1.6
        elif place == "above":
            top = c.y() - 4 - vh - sh
        else:
            top = c.y() - (vh + sh) / 2.0
        center = QtCore.Qt.AlignmentFlag.AlignCenter
        if value:
            p.setFont(vfont)
            p.setPen(text_color)
            p.drawText(QtCore.QRectF(c.x() - room, top, 2 * room, vh), center,
                       _elide(p.fontMetrics(), value, room))
            top += vh
        if sub:
            p.setFont(self.font())
            p.setPen(dim_color)
            p.drawText(QtCore.QRectF(c.x() - room, top, 2 * room, sh), center,
                       _elide(sfm, sub, room))
        p.setFont(self.font())

    def _paint_legend(self, p, owner, rect, text_color, dim_color):
        if rect.isNull() or rect.height() <= 0:
            return
        rows, row_h, swatch, _label_w, range_w = self._legend_metrics(owner)
        fm = self.fontMetrics()
        fit = max(0, int(rect.height() // row_h))
        label_w = rect.width() - 2 - swatch - _GAP - range_w - _GAP - 2
        left = QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        right = QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        y = rect.top()
        for _index, label, range_text, color in rows[:fit]:
            sw = QtCore.QRectF(rect.left() + 2, y + row_h / 2.0 - swatch / 2.0, swatch, swatch)
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QColor(color))
            p.drawRoundedRect(sw, 2, 2)
            x = sw.right() + _GAP
            if label_w > 0:
                p.setPen(text_color)
                p.drawText(QtCore.QRectF(x, y, label_w, row_h), left, _elide(fm, label, label_w))
                x += label_w + _GAP
            p.setPen(dim_color)
            p.drawText(QtCore.QRectF(x, y, range_w, row_h), right, range_text)
            y += row_h

    # -- input --------------------------------------------------------------

    def _on_dial(self, owner, pos) -> bool:
        d = pos - self._center
        return self._radius > 0 and owner._dial_hit(d.x(), d.y(), self._radius)

    def mousePressEvent(self, event):
        owner = self._owner()
        if owner is None or event.button() != QtCore.Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        if self._on_dial(owner, event.position()):
            owner._gauge_clicked()
        event.accept()

    def mouseMoveEvent(self, event):
        owner = self._owner()
        if owner is not None:
            over = self._on_dial(owner, event.position())
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor if over
                           else QtCore.Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event):
        owner = self._owner()
        Key = QtCore.Qt.Key
        if owner is not None and event.key() in (Key.Key_Return, Key.Key_Enter, Key.Key_Space):
            owner._gauge_clicked()
            event.accept()
            return
        super().keyPressEvent(event)

    def event(self, event):
        if event.type() == QtCore.QEvent.Type.ToolTip:
            owner = self._owner()
            text = ""
            if owner is not None:
                # Labels are data: shown literally.  The help text is passed
                # as is, like every other Qt widget's tooltip.
                if self._on_dial(owner, QtCore.QPointF(event.pos())):
                    text = _plain_tooltip(owner._tooltip())
                else:
                    text = owner.helpText()
            if text:
                QtWidgets.QToolTip.showText(event.globalPos(), text, self)
            else:
                QtWidgets.QToolTip.hideText()
                event.ignore()
            return True
        return super().event(event)


class YChartGaugeQt(YChartGaugeBase):
    """Gauge (radial dial) painted with QPainter."""

    def __init__(self, parent=None, label: str = ""):
        # Attributes first: addChild() on the parent may build us immediately.
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        super().__init__(parent, label)

    def _create_backend_widget(self):
        canvas = _GaugeCanvas(self)
        try:
            expand = QtWidgets.QSizePolicy.Policy.Expanding
            preferred = QtWidgets.QSizePolicy.Policy.Preferred
            canvas.setSizePolicy(
                expand if (self.stretchable(YUIDimension.YD_HORIZ) or self.weight(YUIDimension.YD_HORIZ)) else preferred,
                expand if (self.stretchable(YUIDimension.YD_VERT) or self.weight(YUIDimension.YD_VERT)) else preferred)
            canvas.setEnabled(bool(self._enabled))
            canvas.setVisible(self.visible())
            canvas.setAccessibleName(self._label or "Gauge")
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
            canvas.setAccessibleName(self._label or "Gauge")
            canvas.setAccessibleDescription(self._tooltip())
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
        # Shown by _GaugeCanvas.event() when the pointer is not over the dial.
        super().setHelpText(help_text)
