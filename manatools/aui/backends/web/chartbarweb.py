"""
Web backend ChartBar implementation.

The chart is generated server-side as inline SVG from YChartBarBase
(_value_axis(), _bar_geometry()): value axis with tick labels and optional
gridlines, category labels, bars and optional value labels; the series
legend is an HTML list.  No script, no remote content.  Bars carry
``data-bar="c,s"``; manatools.js turns a click (or Enter/Space) into an
Activated event with ``data: {bar: [c, s]}``, routed by YDialogWeb to
_handle_bar_click().

The SVG uses a fixed coordinate system scaled by CSS; text widths are
estimated (the server cannot measure fonts), so long labels are cut with
an ellipsis and crowded category labels are thinned out.

Author: Matteo Pasotti <xquiet@coriolite.com>

License: LGPLv2+
"""

import math

from ...yui_common import YChartBarBase, YChartBarOrientation, YChartLegendPosition
from .commonweb import escape_attr, escape_html, widget_attrs

_W, _H = 400.0, 240.0       # base viewBox; grows with many categories
_FONT = 10.0                # SVG text size, viewBox units
_CHAR = _FONT * 0.6         # estimated average glyph width
_PAD = 6.0
_ROW = 14.0                 # min category slot (horizontal) in units
_MAX_LABEL_CHARS = 18


def _num(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _cut(text: str, chars: int) -> str:
    if chars <= 0:
        return ""
    return text if len(text) <= chars else text[:max(0, chars - 1)] + "…"


def _text_w(text: str) -> float:
    return len(text) * _CHAR


class YChartBarWeb(YChartBarBase):
    """Bar chart rendered as inline SVG plus an HTML series legend."""

    def __init__(self, parent=None, label: str = ""):
        super().__init__(parent, label)

    # -- backend hooks ------------------------------------------------------

    def _apply_chart(self):
        self._notify_update()

    def setHelpText(self, help_text: str):
        super().setHelpText(help_text)
        self._notify_update()

    def setVisible(self, visible: bool = True):
        self._visible = bool(visible)
        self._notify_update()

    def _set_backend_enabled(self, enabled: bool):
        self._notify_update()

    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)

    def _handle_bar_click(self, bar) -> bool:
        """Browser reported a click on bar ``[c, s]`` (untrusted input)."""
        if not self.isEnabled() or not self.visible():
            return False
        if not isinstance(bar, (list, tuple)) or len(bar) != 2:
            return False
        if any(isinstance(v, bool) or not isinstance(v, int) for v in bar):
            return False
        return self._bar_clicked(bar[0], bar[1])

    # -- rendering ----------------------------------------------------------

    def _render_svg(self) -> str:
        n = len(self._categories)
        horizontal = self._orientation == YChartBarOrientation.Horizontal
        vmin, vmax, ticks = self._value_axis()
        tick_texts = [self._format_tick(t) for t in ticks]
        cat_texts = [_cut(c, _MAX_LABEL_CHARS) for c in self._categories]

        if horizontal:
            width = _W
            height = max(_H, n * _ROW + _FONT + 3 * _PAD)
            left = _PAD + max((_text_w(t) for t in cat_texts), default=0) + _PAD
            left = min(left, width * 0.4)
            right = width - _PAD - _text_w(tick_texts[-1]) / 2
            top = _PAD
            bottom = height - _FONT - 2 * _PAD
        else:
            width = max(_W, n * 8.0 + 60.0)
            height = _H
            left = _PAD + max(_text_w(t) for t in tick_texts) + _PAD
            right = width - _PAD
            top = _PAD + _FONT / 2
            bottom = height - _FONT - 2 * _PAD
        pw, ph = max(1.0, right - left), max(1.0, bottom - top)
        span = (vmax - vmin) or 1.0

        def vpos(v):    # data value -> coordinate along the value axis
            if horizontal:
                return left + (v - vmin) / span * pw
            return bottom - (v - vmin) / span * ph

        def upos(u):    # category-axis fraction -> coordinate
            return (top + u * ph) if horizontal else (left + u * pw)

        label = escape_attr(self._label or "Bar chart")
        parts = [f'<svg class="mana-chartbar-svg" viewBox="0 0 {_num(width)} {_num(height)}"'
                 f' role="img" aria-label="{label}" font-size="{_num(_FONT)}">']

        # value axis: gridlines, zero line, tick labels
        for t, text in zip(ticks, tick_texts):
            p = vpos(t)
            cls = "mana-chartbar-zero" if t == 0 else "mana-chartbar-grid"
            if t == 0 or self._show_grid:
                if horizontal:
                    parts.append(f'<line class="{cls}" x1="{_num(p)}" y1="{_num(top)}"'
                                 f' x2="{_num(p)}" y2="{_num(bottom)}"/>')
                else:
                    parts.append(f'<line class="{cls}" x1="{_num(left)}" y1="{_num(p)}"'
                                 f' x2="{_num(right)}" y2="{_num(p)}"/>')
            if horizontal:
                parts.append(f'<text class="mana-chartbar-tick" x="{_num(p)}"'
                             f' y="{_num(bottom + _PAD + _FONT * 0.8)}" text-anchor="middle">'
                             f'{escape_html(text)}</text>')
            else:
                parts.append(f'<text class="mana-chartbar-tick" x="{_num(left - _PAD / 2)}"'
                             f' y="{_num(p + _FONT * 0.35)}" text-anchor="end">'
                             f'{escape_html(text)}</text>')
        if horizontal:
            parts.append(f'<line class="mana-chartbar-axis" x1="{_num(left)}" y1="{_num(bottom)}"'
                         f' x2="{_num(right)}" y2="{_num(bottom)}"/>')
        else:
            parts.append(f'<line class="mana-chartbar-axis" x1="{_num(left)}" y1="{_num(top)}"'
                         f' x2="{_num(left)}" y2="{_num(bottom)}"/>')

        if n == 0 or not self._series:
            parts.append(f'<text class="mana-chartbar-empty" x="{_num(left + pw / 2)}"'
                         f' y="{_num(top + ph / 2)}" text-anchor="middle"'
                         f' dominant-baseline="middle">No data</text></svg>')
            return "".join(parts)

        # category labels (thinned out when they would overlap)
        slot = (ph if horizontal else pw) / n
        if horizontal:
            every = max(1, math.ceil(_FONT / slot))
            chars = max(1, int((left - 2 * _PAD) / _CHAR))
        else:
            longest = max(len(t) for t in cat_texts)
            want = (min(longest, 6) + 1) * _CHAR      # keep labels readable
            every = max(1, math.ceil(want / slot))
            chars = max(1, int(slot * every / _CHAR) - 1)
        for c in range(0, n, every):
            text = escape_html(_cut(self._categories[c], min(chars, _MAX_LABEL_CHARS)))
            mid = upos((c + 0.5) / n)
            if horizontal:
                parts.append(f'<text class="mana-chartbar-category" x="{_num(left - _PAD / 2)}"'
                             f' y="{_num(mid + _FONT * 0.35)}" text-anchor="end">{text}</text>')
            else:
                parts.append(f'<text class="mana-chartbar-category" x="{_num(mid)}"'
                             f' y="{_num(bottom + _PAD + _FONT * 0.8)}" text-anchor="middle">{text}</text>')

        # bars
        selected = self._sel
        values = []
        for c, s, u0, u1, v0, v1, color in self._bar_geometry():
            a, b = upos(u0), upos(u1)
            p0, p1 = vpos(v0), vpos(v1)
            if horizontal:
                x, y, w, h = min(p0, p1), a, abs(p1 - p0), b - a
            else:
                x, y, w, h = a, min(p0, p1), b - a, abs(p1 - p0)
            classes = "mana-chartbar-bar"
            if (c, s) == selected:
                classes += " mana-chartbar-selected"
            tip = self._bar_tooltip(c, s)
            parts.append(
                f'<rect class="{classes}" data-bar="{c},{s}" tabindex="0" role="button"'
                f' aria-label="{escape_attr(tip)}" fill="{escape_attr(color)}"'
                f' x="{_num(x)}" y="{_num(y)}" width="{_num(max(w, 0.5))}" height="{_num(max(h, 0.5))}">'
                f'<title>{escape_html(tip)}</title></rect>')
            if self._show_values:
                values.append((c, s, x, y, w, h, v1 >= v0))

        # value labels: inside the segment when stacked, else past the bar end
        for c, s, x, y, w, h, up in values:
            text = escape_html(self._value_text(c, s))
            tw = _text_w(self._value_text(c, s))
            if self._stacked:
                if (w if horizontal else h) < (tw + 2 if horizontal else _FONT + 2):
                    continue
                tx, ty, anchor = x + w / 2, y + h / 2 + _FONT * 0.35, "middle"
                cls = "mana-chartbar-value mana-chartbar-value-inside"
            elif horizontal:
                ty = y + h / 2 + _FONT * 0.35
                cls = "mana-chartbar-value"
                if up and x + w + 2 + tw <= right:
                    tx, anchor = x + w + 2, "start"
                elif not up and x - 2 - tw >= left:
                    tx, anchor = x - 2, "end"
                else:   # no room past the end: inside, at the end
                    tx, anchor = (x + w - 2, "end") if up else (x + 2, "start")
                    cls += " mana-chartbar-value-inside"
            else:
                tx, anchor = x + w / 2, "middle"
                cls = "mana-chartbar-value"
                if up and y - 2 - _FONT >= top - _FONT / 2:
                    ty = y - 2
                elif not up and y + h + _FONT <= bottom:
                    ty = y + h + _FONT
                else:   # no room past the end: inside, at the end
                    ty = y + _FONT if up else y + h - 2
                    cls += " mana-chartbar-value-inside"
            parts.append(f'<text class="{cls}" x="{_num(tx)}" y="{_num(ty)}"'
                         f' text-anchor="{anchor}">{text}</text>')

        parts.append('</svg>')
        return "".join(parts)

    def _render_legend(self) -> str:
        rows = self._legend_rows()
        if (self._legend_position == YChartLegendPosition.Hidden or not rows
                or not any(name for _s, name, _c in rows)):
            return ""
        items = []
        for s, name, color in rows:
            classes = "mana-chartbar-legend-row"
            if s == self._sel[1]:
                classes += " mana-chartbar-selected"
            items.append(
                f'<li class="{classes}">'
                f'<svg class="mana-chartbar-swatch" viewBox="0 0 10 10" aria-hidden="true">'
                f'<rect width="10" height="10" rx="2" fill="{escape_attr(color)}"/></svg>'
                f'<span class="mana-chartbar-legend-label">{escape_html(name)}</span></li>')
        return f'<ul class="mana-chartbar-legend">{"".join(items)}</ul>'

    def render(self) -> str:
        extra = ["mana-chartbar-legend-" + self._legend_position.name.lower(),
                 "mana-chartbar-" + self._orientation.name.lower()]
        if not self._enabled:
            extra.append("mana-disabled")
        attrs = widget_attrs(self.id(), "YChartBar", True, self._visible,
                             " ".join(extra),
                             extra_attrs={"title": self.helpText() or None})
        title = (f'<div class="mana-chartbar-title">{escape_html(self._label)}</div>'
                 if self._label else "")
        return (f'<div {attrs}>{title}'
                f'<div class="mana-chartbar-body">'
                f'<div class="mana-chartbar-plot">{self._render_svg()}</div>'
                f'{self._render_legend()}'
                f'</div></div>')
