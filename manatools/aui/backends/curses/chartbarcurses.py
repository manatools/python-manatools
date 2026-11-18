# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Curses backend YChartBar.

Always drawn horizontally (a terminal has many more columns than rows):

- grouped: one row per (category, series): category label on the first row
  of its group, series name next to it when there are several series;
- stacked: one row per category with one colored segment per series,
  negative segments left of the zero column.

Bars are full blocks scaled to the shared value axis; the zero column is
marked when the axis has negative values.  An axis row under the bars shows
the range (min, 0, max).  A one-line series legend sits above the bars
(legendPosition() Hidden drops it; Right and Bottom look the same here), and
setShowValues(True) adds a value column (stacked: the category total).
Colors and glyphs come from commoncurses.chart_color_attr() /
chart_glyphs() like YChartPie; without working colors, stacked segments and
their legend entries are told apart by fill patterns (grouped rows already
carry the series name), and ASCII glyphs replace the Unicode blocks where
those cannot be shown.

orientation() is kept in the model but has no effect here.

Keys: Up/Down (Home/End, PgUp/PgDn) move between rows, Left/Right between
the segments of a stacked row; Enter/Space activate the selected bar.

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


class YChartBarCurses(YChartBarBase):
    """Bar chart shown as horizontal block bars."""

    def __init__(self, parent=None, label: str = ""):
        # Attributes first: addChild() on the parent may draw us immediately.
        self._can_focus = True
        self._focused = False
        self._scroll_offset = 0
        self._visible_rows = 0
        self._height = 1
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        super().__init__(parent, label)
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
        return (self._legend_position != YChartLegendPosition.Hidden
                and any(name for name, _c in self._series))

    def _header_count(self) -> int:
        return (1 if self._label else 0) + (1 if self._show_legend() else 0)

    def _rows_model(self) -> list:
        """Body rows as (category, series); series is -1 for a stacked row."""
        if not self._series:
            return []
        if self._stacked:
            return [(c, -1) for c in range(len(self._categories))]
        return [(c, s) for c in range(len(self._categories)) for s in range(len(self._series))]

    def _update_height(self):
        # Minimal height: header + a few rows + axis; stretchable for the rest.
        self._height = self._header_count() + max(1, min(len(self._rows_model()), 3)) + 1

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
        return 24

    def key_hints(self) -> str:
        ascii_only = chart_glyphs().ascii
        if self._stacked:
            return _("Arrows=Move ENTER=Activate") if ascii_only else _("↑↓←→=Move ENTER=Activate")
        return _("Up/Down=Move ENTER=Activate") if ascii_only else _("↑↓=Move ENTER=Activate")

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

    def _row_of_selection(self, rows) -> int:
        c, s = self._sel
        if c < 0:
            return -1
        key = (c, -1) if self._stacked else (c, s)
        try:
            return rows.index(key)
        except ValueError:
            return -1

    def _draw(self, window, y, x, width, height):
        if not self._visible or width <= 0 or height <= 0:
            return
        try:
            self._draw_chart(window, y, x, width, height)
        except Exception:
            self._logger.exception("_draw failed")

    def _draw_chart(self, window, y, x, width, height):
        dim = 0 if self.isEnabled() else curses.A_DIM
        bottom = y + height
        g = chart_glyphs(window)
        # Colors that actually work (pairs can run out even with has_colors()).
        attrs = [chart_color_attr(self.seriesColor(si)) for si in range(len(self._series))]
        colors = any(attrs)
        # Without colors, stacked segments (and their legend entries) use patterns.
        patterned = self._stacked and not colors

        if self._label:
            self._put(window, y, x, _cut(self._label, width, g.ellipsis), curses.A_BOLD | dim)
            y += 1
        if self._show_legend() and y < bottom:
            cx = x
            for s, name, color in self._legend_rows():
                mark = g.patterns[s % len(g.patterns)] if patterned else g.swatch
                cell = f"{mark} {name}  "
                if cx + len(cell) > x + width:
                    self._put(window, y, cx, _cut(g.ellipsis, x + width - cx, g.ellipsis), dim)
                    break
                self._put(window, y, cx, mark, attrs[s] | dim)
                attr = (curses.A_BOLD if s == self._sel[1] else 0) | dim
                self._put(window, y, cx + 2, name, attr)
                cx += len(cell)
            y += 1

        rows = self._rows_model()
        if not rows:
            if y < bottom:
                self._put(window, y, x, _cut(_("No data"), width, g.ellipsis), curses.A_DIM)
            return

        avail = bottom - y - 1          # last row: axis
        if avail <= 0:
            return
        more = len(rows) > avail
        visible = avail - 1 if more and avail > 1 else avail
        self._visible_rows = visible
        sel_row = self._row_of_selection(rows)
        if sel_row >= 0:
            if sel_row < self._scroll_offset:
                self._scroll_offset = sel_row
            elif sel_row >= self._scroll_offset + visible:
                self._scroll_offset = sel_row - visible + 1
        self._scroll_offset = max(0, min(self._scroll_offset, max(0, len(rows) - visible)))
        start = self._scroll_offset
        shown = rows[start:start + visible]

        # columns: category | series (grouped, several series) | bars | value
        k = len(self._series)
        label_w = min(max((len(c) for c in self._categories), default=0), max(4, width // 4))
        series_w = 0
        if not self._stacked and k > 1:
            series_w = min(max(len(n) for n, _c in self._series), max(3, width // 6))
        if self._show_values:
            if self._stacked:
                texts = [self._format_value(sum(r)) for r in self._rows]
            else:
                texts = [self._format_value(v) for r in self._rows for v in r]
            value_w = max((len(t) for t in texts), default=0)
        else:
            value_w = 0
        bar_x = x + label_w + 1 + (series_w + 1 if series_w else 0)
        bar_w = width - (bar_x - x) - ((value_w + 1) if value_w else 0)
        if bar_w < 4:
            bar_w = max(1, width - (bar_x - x))
            value_w = 0

        vmin, vmax, _ticks = self._value_axis()
        span = (vmax - vmin) or 1.0

        def col(v):
            return int(round((v - vmin) / span * bar_w))

        zero = min(bar_w - 1, col(0.0))
        mark_zero = vmin < 0

        for c, s in shown:
            current = (c, s) == (self._sel if not self._stacked else (self._sel[0], -1))
            row_attr = (curses.A_REVERSE if (current and self._focused) else
                        (curses.A_BOLD if current else 0)) | dim
            first = self._stacked or s == 0
            if first:
                self._put(window, y, x, f"{_cut(self._categories[c], label_w, g.ellipsis):<{label_w}}", row_attr)
            elif current:
                self._put(window, y, x, " " * label_w, row_attr)
            if series_w:
                self._put(window, y, x + label_w + 1,
                          f"{_cut(self._series[s][0], series_w, g.ellipsis):<{series_w}}", row_attr)
            if mark_zero:
                self._put(window, y, bar_x + zero, g.zero, curses.A_DIM)
            segments = []
            if self._stacked:
                pos = neg = 0.0
                for si, v in enumerate(self._rows[c]):
                    if v > 0:
                        segments.append((si, pos, pos + v))
                        pos += v
                    elif v < 0:
                        segments.append((si, neg + v, neg))
                        neg += v
            else:
                v = self._rows[c][s]
                if v:
                    segments.append((s, min(0.0, v), max(0.0, v)))
            for si, lo, hi in segments:
                a, b = col(lo), col(hi)
                if b <= a:              # too small for a cell: show one anyway
                    if hi > 0:
                        b = a + 1
                    else:
                        a = b - 1
                if mark_zero and lo >= 0 and a <= zero:
                    a, b = zero + 1, max(b, zero + 2)   # keep the zero line visible
                a, b = max(0, a), min(bar_w, b)
                if b <= a:
                    continue
                fill = g.patterns[si % len(g.patterns)] if patterned else g.block
                attr = attrs[si] | dim
                if self._stacked and (c, si) == self._sel:
                    attr |= curses.A_REVERSE if self._focused else curses.A_BOLD
                self._put(window, y, bar_x + a, fill * (b - a), attr)
            if value_w:
                total = sum(self._rows[c]) if self._stacked else self._rows[c][s]
                self._put(window, y, bar_x + bar_w + 1,
                          f"{self._format_value(total):>{value_w}}", row_attr)
            y += 1

        if more and y < bottom - 1:
            parts = []
            if start:
                parts.append(f"{g.up}{start}")
            hidden_below = len(rows) - start - len(shown)
            if hidden_below:
                parts.append(f"{g.down}{hidden_below}")
            self._put(window, y, x, _cut(g.ellipsis + " " + " ".join(parts), width, g.ellipsis), curses.A_DIM)
            y += 1

        # axis row: min at the bar start, 0 at the zero column, max at the end
        if y < bottom:
            axis = [" "] * bar_w
            lo_t, hi_t, z_t = self._format_tick(vmin), self._format_tick(vmax), "0"
            for i, ch in enumerate(lo_t[:bar_w]):
                axis[i] = ch
            for i, ch in enumerate(hi_t[-bar_w:]):
                axis[bar_w - len(hi_t[-bar_w:]) + i] = ch
            if mark_zero:
                zs = zero - len(z_t) // 2
                if zs > len(lo_t) and zs + len(z_t) < bar_w - len(hi_t):
                    axis[zs] = z_t
            self._put(window, y, bar_x, "".join(axis), curses.A_DIM)

    # -- input --------------------------------------------------------------

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled() or not self.visible():
            return False
        rows = self._rows_model()
        if not rows:
            return False
        c, s = self._sel
        if key in (ord(' '), ord('\n'), ord('\r'), curses.KEY_ENTER):
            if c < 0:
                return False        # nothing selected: let Enter reach the default button
            self._bar_clicked(c, s)
            return True
        k = len(self._series)
        if self._stacked and key in (curses.KEY_LEFT, curses.KEY_RIGHT):
            if c < 0:
                c, s = 0, 0
            else:
                s = max(0, s - 1) if key == curses.KEY_LEFT else min(k - 1, s + 1)
            self.setSelectedBar(c, s)
            return True
        cur = self._row_of_selection(rows)
        page = max(1, self._visible_rows)
        if key == curses.KEY_DOWN:
            new = min(len(rows) - 1, cur + 1) if cur >= 0 else 0
        elif key == curses.KEY_UP:
            new = max(0, cur - 1) if cur >= 0 else len(rows) - 1
        elif key == curses.KEY_HOME:
            new = 0
        elif key == curses.KEY_END:
            new = len(rows) - 1
        elif key == curses.KEY_NPAGE:
            new = min(len(rows) - 1, max(cur, 0) + page)
        elif key == curses.KEY_PPAGE:
            new = max(0, cur - page)
        else:
            return False
        nc, ns = rows[new]
        if ns < 0:                      # stacked row: keep the series
            ns = s if 0 <= s < k else 0
        if (nc, ns) != self._sel:
            self.setSelectedBar(nc, ns)
        return True
