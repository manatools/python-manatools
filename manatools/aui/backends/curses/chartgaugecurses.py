# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Curses backend YChartGauge.

A terminal has no room for a round dial, so the gauge is a horizontal meter
(top to bottom, each row only when it has something to show):

    CPU                                  title (bold)
    72% load                             value text (bold) + subtitle (dim)
    ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀  band strip, colored per band
    █████████████████████████░░░░░│░░░░  value bar from the fill origin,
                                         target marker
    0      20     40     60     80   100 tick labels
    ■ OK 0..60  ■ Warning 60..85  ...    legend of the labelled bands

The value bar takes the band color of the value, like the other backends.
sweepAngle() and showNeedle() have no effect here.  Colors and glyphs come
from commoncurses.chart_color_attr() / chart_glyphs(); without working
colors the band strip and the legend swatches use fill patterns, and ASCII
glyphs replace the Unicode blocks where those cannot be shown.

The gauge has a fixed height, so it does not stretch vertically here.

Keys: Enter/Space activate.

License: LGPLv2+

@package manatools.aui.backends.curses
'''
import curses
import logging
import gettext

from ...yui_common import *
from .commoncurses import _curses_help_text_changed, chart_color_attr, chart_glyphs

_ = gettext.gettext


def _cut(text: str, width: int, ellipsis: str = "…") -> str:
    if width <= 0:
        return ""
    return text if len(text) <= width else text[:max(0, width - 1)] + ellipsis


class YChartGaugeCurses(YChartGaugeBase):
    """Gauge shown as a horizontal meter."""

    def __init__(self, parent=None, label: str = ""):
        # Attributes first: addChild() on the parent may draw us immediately.
        self._can_focus = True
        self._focused = False
        self._height = 2
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        super().__init__(parent, label)
        self.setStretchable(YUIDimension.YD_VERT, False)
        self._update_height()

    def _create_backend_widget(self):
        self._backend_widget = self
        self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())

    # -- backend hooks ------------------------------------------------------

    def _apply_chart(self):
        self._update_height()
        dlg = self.findDialog()
        if dlg is not None:
            try:
                dlg.mark_dirty()
            except Exception:
                pass

    def _show_legend(self) -> bool:
        return self._legend_position != YChartLegendPosition.Hidden and bool(self._legend_rows())

    def _row_plan(self) -> list:
        """Names of the rows drawn, top to bottom."""
        rows = []
        if self._label:
            rows.append("title")
        if self._show_value or self._subtitle:
            rows.append("value")
        if self._band_arcs():
            rows.append("strip")
        rows.append("bar")
        if self._show_ticks:
            rows.append("ticks")
        if self._show_legend():
            rows.append("legend")
        return rows

    def _update_height(self):
        self._height = len(self._row_plan())

    # -- common widget API --------------------------------------------------

    def setHelpText(self, help_text: str):
        super().setHelpText(help_text)
        _curses_help_text_changed(self)

    def setVisible(self, visible=True):
        super().setVisible(visible)
        self._can_focus = bool(visible)

    def _set_backend_enabled(self, enabled):
        self._can_focus = bool(enabled) and self.visible()
        if not enabled:
            self._focused = False

    def minWidth(self):
        return 16

    def key_hints(self) -> str:
        return _("ENTER=Activate")

    # -- drawing ------------------------------------------------------------

    @staticmethod
    def _put(window, y, x, text, attr=0):
        # Labels are data: control characters (newline, tab, backspace...)
        # would move the cursor and scramble other rows.  One-for-one
        # replacement keeps the column widths computed with len().
        if not text.isprintable():
            text = "".join(ch if ch.isprintable() else "?" for ch in text)
        try:
            window.addstr(y, x, text, attr)
        except curses.error:
            pass

    def _draw(self, window, y, x, width, height):
        if not self._visible or width <= 0 or height <= 0:
            return
        try:
            self._draw_gauge(window, y, x, width, height)
        except Exception:
            self._logger.exception("_draw failed")

    def _col(self, v: float, width: int) -> int:
        """Cell boundary (0..width) of value *v*, clamped to the range."""
        frac = (self._clamp(v) - self._min) / (self._max - self._min)
        return int(round(frac * width))

    def _draw_gauge(self, window, y, x, width, height):
        dim = 0 if self.isEnabled() else curses.A_DIM
        g = chart_glyphs(window)
        bottom = y + height
        band_attrs = [chart_color_attr(self.bandColor(i)) for i in range(len(self._bands))]
        value_attr = chart_color_attr(self._current_color())
        colors = bool(value_attr) or any(band_attrs)
        focus = (curses.A_REVERSE if self._focused else 0)
        # The first text row shows keyboard focus.
        focus_row = "value" if (self._show_value or self._subtitle) else "title"

        for row in self._row_plan():
            if y >= bottom:
                break
            if row == "title":
                attr = curses.A_BOLD | dim | (focus if focus_row == "title" else 0)
                self._put(window, y, x, _cut(self._label, width, g.ellipsis), attr)
            elif row == "value":
                cx = x
                if self._show_value:
                    text = _cut(self._value_text(), width, g.ellipsis)
                    self._put(window, y, cx, text, curses.A_BOLD | dim | focus)
                    cx += len(text) + 1
                if self._subtitle and cx < x + width:
                    self._put(window, y, cx, _cut(self._subtitle, x + width - cx, g.ellipsis),
                              curses.A_DIM | (0 if self._show_value else focus))
            elif row == "strip":
                self._draw_strip(window, y, x, width, g, band_attrs, colors, dim)
            elif row == "bar":
                self._draw_bar(window, y, x, width, g, value_attr, dim,
                               focus if focus_row == "title" and not self._label else 0)
            elif row == "ticks":
                self._draw_ticks(window, y, x, width)
            elif row == "legend":
                self._draw_legend(window, y, x, width, g, band_attrs, colors, dim)
            y += 1

    @staticmethod
    def _band_pattern(g, band: int) -> str:
        """Fill pattern of *band* without colors: the shaded ones, so no band
        looks like the solid value bar."""
        shades = g.patterns[1:]
        return shades[band % len(shades)]

    def _draw_strip(self, window, y, x, width, g, band_attrs, colors, dim):
        """One cell per column, in the color (or pattern) of its band."""
        span = self._max - self._min
        run_start, run_band = 0, None
        for i in range(width + 1):
            band = -2
            if i < width:
                band = self._band_at(self._min + (i + 0.5) / width * span)
            if band != run_band:
                if run_band is not None and run_band >= 0:
                    glyph = g.strip if colors else self._band_pattern(g, run_band)
                    self._put(window, y, x + run_start, glyph * (i - run_start), band_attrs[run_band] | dim)
                run_start, run_band = i, band

    def _draw_bar(self, window, y, x, width, g, value_attr, dim, extra):
        a = self._col(self._fill_origin(), width)
        b = self._col(self._value, width)
        if a > b:
            a, b = b, a
        if a == b and self._value != self._fill_origin():
            # Too small for a cell: show one anyway.
            if b < width:
                b += 1
            else:
                a -= 1
        self._put(window, y, x, g.track * width, curses.A_DIM | extra)
        if b > a:
            self._put(window, y, x + a, g.block * (b - a), value_attr | dim | extra)
        if self._target_angle() is not None:
            t = min(width - 1, self._col(self._target, width))
            on_fill = a <= t < b
            self._put(window, y, x + t, g.zero,
                      curses.A_BOLD | dim | (curses.A_REVERSE if on_fill else 0))

    def _draw_ticks(self, window, y, x, width):
        """Tick labels at their columns: both ends always, inner ones when
        they do not touch a neighbour."""
        ticks = self._ticks()
        cells = [" "] * width
        placed = []         # (start, end) columns taken

        def place(start, text):
            start = max(0, min(start, width - len(text)))
            end = start + len(text)
            if start < 0 or end > width:
                return
            if any(start <= e and end >= s for s, e in placed):
                return
            placed.append((start, end))
            cells[start:end] = list(text)

        if not ticks:
            return
        place(0, ticks[0][2])
        last = ticks[-1][2]
        place(width - len(last), last)
        for v, _angle, text in ticks[1:-1]:
            place(self._col(v, width) - len(text) // 2, text)
        self._put(window, y, x, "".join(cells).rstrip(), curses.A_DIM)

    def _draw_legend(self, window, y, x, width, g, band_attrs, colors, dim):
        cx = x
        for i, label, range_text, _color in self._legend_rows():
            mark = g.swatch if colors else self._band_pattern(g, i)
            cell = f"{mark} {label} {range_text}  "
            if cx + len(cell) > x + width:
                self._put(window, y, cx, _cut(g.ellipsis, x + width - cx, g.ellipsis), dim)
                break
            self._put(window, y, cx, mark, band_attrs[i] | dim)
            self._put(window, y, cx + 2, label, dim)
            self._put(window, y, cx + 3 + len(label), range_text, curses.A_DIM)
            cx += len(cell)

    # -- input --------------------------------------------------------------

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled() or not self.visible():
            return False
        if key in (ord(' '), ord('\n'), ord('\r'), curses.KEY_ENTER):
            return self._gauge_clicked()
        return False
