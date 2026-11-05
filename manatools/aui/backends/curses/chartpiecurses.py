# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Curses backend YChartPie.

A terminal cannot draw a disc, so the pie is shown as its legend turned into
a bar chart: one row per slice with a colored block, label, value, percent
and a bar whose length is the slice share of the total.  An optional title
row comes first; in donut mode the center text is shown under it.

Slice colors and glyphs come from commoncurses.chart_color_attr() /
chart_glyphs(): 256/88-color cubes, fixed distinct colors on 16/8-color
terminals, none on monochrome ones (labels identify the rows), ASCII glyphs
where Unicode blocks cannot be shown.

legendPosition() Hidden drops the label/value/percent columns (bars only);
Right and Bottom look the same here.

Keys: Up/Down (Home/End, PgUp/PgDn) move the selection, Enter/Space activate
the selected slice.

License: LGPLv2+

@package manatools.aui.backends.curses
'''
import curses
import logging
import gettext

from ...yui_common import *
from .commoncurses import _curses_help_text_changed, chart_color_attr, chart_glyphs

_ = gettext.gettext


class YChartPieCurses(YChartPieBase):
    """Pie chart shown as a navigable bar list."""

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

    def _header_rows(self) -> list:
        """(text, attr) rows drawn above the slices."""
        rows = []
        if self._label:
            rows.append((self._label, curses.A_BOLD))
        if self._donut_ratio > 0 and self._center_text:
            rows.append((self._center_text, curses.A_DIM))
        return rows

    def _update_height(self):
        # Minimal height: header + a few slices; stretchable for the rest.
        self._height = len(self._header_rows()) + max(1, min(len(self._slices), 3))

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
        return 20

    def key_hints(self) -> str:
        if chart_glyphs().ascii:
            return _("Up/Down=Move ENTER=Activate")
        return _("↑↓=Move ENTER=Activate")

    # -- drawing ------------------------------------------------------------

    def _ensure_selected_visible(self, rows: int):
        sel = self._selected
        if rows <= 0 or sel < 0:
            self._scroll_offset = max(0, min(self._scroll_offset, max(0, len(self._slices) - rows)))
            return
        if sel < self._scroll_offset:
            self._scroll_offset = sel
        elif sel >= self._scroll_offset + rows:
            self._scroll_offset = sel - rows + 1

    def _draw(self, window, y, x, width, height):
        if not self._visible or width <= 0 or height <= 0:
            return
        try:
            self._draw_rows(window, y, x, width, height)
        except Exception:
            self._logger.exception("_draw failed")

    @staticmethod
    def _put(window, y, x, text, attr=0):
        try:
            window.addstr(y, x, text, attr)
        except curses.error:
            pass

    def _draw_rows(self, window, y, x, width, height):
        g = chart_glyphs(window)
        dim = 0 if self.isEnabled() else curses.A_DIM
        bottom = y + height
        for text, attr in self._header_rows():
            if y >= bottom:
                return
            self._put(window, y, x, text[:width], attr | dim)
            y += 1

        rows = self._legend_rows()
        if self.total() <= 0:
            if y < bottom:
                self._put(window, y, x, _("No data")[:width], curses.A_DIM)
            if not rows:
                return
            y += 1

        avail = bottom - y
        if avail <= 0:
            return
        more = len(rows) > avail
        visible = avail - 1 if more and avail > 1 else avail
        self._visible_rows = visible
        self._ensure_selected_visible(visible)
        start = self._scroll_offset
        shown = rows[start:start + visible]

        columns = self._legend_position != YChartLegendPosition.Hidden
        value_w = max((len(r[2]) for r in rows), default=0)
        pct_w = 6 if self._show_percent else 0          # "100.0%"
        label_w = 0
        if columns:
            label_w = min(max((len(r[1]) for r in rows), default=0), max(6, width // 3))
        fixed = 2 + ((label_w + 1 + value_w + 1 + (pct_w + 1 if pct_w else 0)) if columns else 0)
        bar_w = max(0, width - fixed)

        for index, label, value_text, pct_text, color in shown:
            cattr = chart_color_attr(color) | dim
            current = index == self._selected
            row_attr = (curses.A_REVERSE if (current and self._focused) else
                        (curses.A_BOLD if current else 0)) | dim
            cx = x
            self._put(window, y, cx, g.swatch + " ", cattr)
            cx += 2
            if columns:
                lab = label if len(label) <= label_w else label[:max(0, label_w - 1)] + g.ellipsis
                cell = f"{lab:<{label_w}} {value_text:>{value_w}} "
                if pct_w:
                    cell += f"{pct_text:>{pct_w}} "
                self._put(window, y, cx, cell[:max(0, x + width - cx)], row_attr)
                cx += len(cell)
            elif current:
                # Bars only: mark the selected row on its swatch.
                self._put(window, y, x, g.swatch, cattr | curses.A_REVERSE)
            if bar_w > 0:
                pct = self.slicePercent(index)
                n = int(round(pct / 100.0 * bar_w))
                if pct > 0 and n == 0:
                    n = 1
                if n:
                    self._put(window, y, cx, g.block * min(n, bar_w), cattr)
            y += 1

        if more and y < bottom:
            hidden_above = start
            hidden_below = len(rows) - start - len(shown)
            parts = []
            if hidden_above:
                parts.append(f"{g.up}{hidden_above}")
            if hidden_below:
                parts.append(f"{g.down}{hidden_below}")
            self._put(window, y, x, (g.ellipsis + " " + " ".join(parts))[:width], curses.A_DIM)

    # -- input --------------------------------------------------------------

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled() or not self.visible():
            return False
        count = len(self._slices)
        if count == 0:
            return False
        cur = self._selected
        page = max(1, self._visible_rows)
        if key == curses.KEY_DOWN:
            new = min(count - 1, cur + 1) if cur >= 0 else 0
        elif key == curses.KEY_UP:
            new = max(0, cur - 1) if cur >= 0 else count - 1
        elif key == curses.KEY_HOME:
            new = 0
        elif key == curses.KEY_END:
            new = count - 1
        elif key == curses.KEY_NPAGE:
            new = min(count - 1, max(cur, 0) + page)
        elif key == curses.KEY_PPAGE:
            new = max(0, cur - page)
        elif key in (ord(' '), ord('\n'), ord('\r'), curses.KEY_ENTER):
            if cur < 0:
                return False        # nothing selected: let Enter reach the default button
            self._slice_clicked(cur)
            return True
        else:
            return False
        if new != cur:
            self.setSelectedSlice(new)
        return True
