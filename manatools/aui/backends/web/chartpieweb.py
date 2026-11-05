"""
Web backend ChartPie implementation.

The pie is generated server-side as inline SVG from YChartPieBase._geometry():
no script, no remote content.  Slices and legend rows carry ``data-slice``;
manatools.js turns a click (or Enter/Space) into an Activated event with
``data: {slice: <index>}``, routed by YDialogWeb to _handle_slice_click().

Author: Matteo Pasotti <xquiet@coriolite.com>

License: LGPLv2+
"""

import math

from ...yui_common import YChartPieBase, YChartLegendPosition
from .commonweb import escape_attr, escape_html, widget_attrs

# SVG user units: the pie is drawn in a VIEW x VIEW box and scaled by CSS.
_VIEW = 200.0
_CX = _CY = _VIEW / 2
_RADIUS = 95.0
_FULL_TURN = 359.999


def _num(v: float) -> str:
    return f"{v:.3f}".rstrip("0").rstrip(".")


def _point(angle_deg: float, radius: float) -> str:
    """SVG point at *angle_deg* (0 = 12 o'clock, clockwise) and *radius*."""
    a = math.radians(angle_deg)
    return f"{_num(_CX + radius * math.sin(a))},{_num(_CY - radius * math.cos(a))}"


def _ring_path(outer: float, inner: float) -> str:
    """Full circle (inner == 0) or full ring; fill-rule evenodd cuts the hole."""
    top, bottom = f"{_num(_CX)},{_num(_CY - outer)}", f"{_num(_CX)},{_num(_CY + outer)}"
    d = (f"M{top} A{_num(outer)},{_num(outer)} 0 1 1 {bottom} "
         f"A{_num(outer)},{_num(outer)} 0 1 1 {top} Z")
    if inner > 0:
        itop, ibottom = f"{_num(_CX)},{_num(_CY - inner)}", f"{_num(_CX)},{_num(_CY + inner)}"
        d += (f" M{itop} A{_num(inner)},{_num(inner)} 0 1 0 {ibottom} "
              f"A{_num(inner)},{_num(inner)} 0 1 0 {itop} Z")
    return d


def _sector_path(start: float, sweep: float, outer: float, inner: float) -> str:
    if sweep >= _FULL_TURN:
        return _ring_path(outer, inner)
    end = start + sweep
    large = 1 if sweep > 180.0 else 0
    r_o = _num(outer)
    if inner <= 0:
        return (f"M{_num(_CX)},{_num(_CY)} L{_point(start, outer)} "
                f"A{r_o},{r_o} 0 {large} 1 {_point(end, outer)} Z")
    r_i = _num(inner)
    return (f"M{_point(start, outer)} A{r_o},{r_o} 0 {large} 1 {_point(end, outer)} "
            f"L{_point(end, inner)} A{r_i},{r_i} 0 {large} 0 {_point(start, inner)} Z")


class YChartPieWeb(YChartPieBase):
    """Pie / donut chart rendered as inline SVG plus an HTML legend."""

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

    def _handle_slice_click(self, index) -> bool:
        """Browser reported a click on slice *index* (untrusted input)."""
        if not self.isEnabled() or not self.visible():
            return False
        if isinstance(index, bool) or not isinstance(index, (int, str)):
            return False
        return self._slice_clicked(index)

    # -- rendering ----------------------------------------------------------

    def _render_svg(self) -> str:
        inner = _RADIUS * self._donut_ratio
        parts = [f'<svg class="mana-chartpie-svg" viewBox="0 0 {_num(_VIEW)} {_num(_VIEW)}"'
                 f' role="img" aria-label="{escape_attr(self._label or "Pie chart")}">']
        geom = self._geometry()
        if not geom:
            parts.append(f'<path class="mana-chartpie-empty" fill-rule="evenodd"'
                         f' d="{_ring_path(_RADIUS, max(inner, _RADIUS * 0.6))}"/>')
            parts.append(f'<text class="mana-chartpie-center" x="{_num(_CX)}" y="{_num(_CY)}"'
                         f' text-anchor="middle" dominant-baseline="middle">No data</text>')
        else:
            for index, start, sweep, color in geom:
                classes = "mana-chartpie-slice"
                if index == self._selected:
                    classes += " mana-chartpie-selected"
                tip = self._slice_tooltip(index)
                parts.append(
                    f'<path class="{classes}" data-slice="{index}" tabindex="0"'
                    f' role="button" aria-label="{escape_attr(tip)}"'
                    f' fill="{escape_attr(color)}" fill-rule="evenodd"'
                    f' d="{_sector_path(start, sweep, _RADIUS, inner)}">'
                    f'<title>{escape_html(tip)}</title></path>')
            if inner > 0 and self._center_text:
                parts.append(f'<text class="mana-chartpie-center" x="{_num(_CX)}" y="{_num(_CY)}"'
                             f' text-anchor="middle" dominant-baseline="middle">'
                             f'{escape_html(self._center_text)}</text>')
        parts.append('</svg>')
        return "".join(parts)

    def _render_legend(self) -> str:
        if self._legend_position == YChartLegendPosition.Hidden or not self._slices:
            return ""
        rows = []
        for index, label, value_text, pct_text, color in self._legend_rows():
            classes = "mana-chartpie-legend-row"
            if index == self._selected:
                classes += " mana-chartpie-selected"
            pct = (f'<span class="mana-chartpie-legend-pct">{escape_html(pct_text)}</span>'
                   if pct_text else "")
            rows.append(
                f'<li class="{classes}" data-slice="{index}" tabindex="0" role="button">'
                f'<svg class="mana-chartpie-swatch" viewBox="0 0 10 10" aria-hidden="true">'
                f'<rect width="10" height="10" rx="2" fill="{escape_attr(color)}"/></svg>'
                f'<span class="mana-chartpie-legend-label">{escape_html(label)}</span>'
                f'<span class="mana-chartpie-legend-value">{escape_html(value_text)}</span>'
                f'{pct}</li>')
        return f'<ul class="mana-chartpie-legend">{"".join(rows)}</ul>'

    def render(self) -> str:
        extra = ["mana-chartpie-legend-"
                 + self._legend_position.name.lower()]
        if not self._enabled:
            extra.append("mana-disabled")
        attrs = widget_attrs(self.id(), "YChartPie", True, self._visible,
                             " ".join(extra),
                             extra_attrs={"title": self.helpText() or None})
        title = (f'<div class="mana-chartpie-title">{escape_html(self._label)}</div>'
                 if self._label else "")
        return (f'<div {attrs}>{title}'
                f'<div class="mana-chartpie-body">'
                f'<div class="mana-chartpie-pie">{self._render_svg()}</div>'
                f'{self._render_legend()}'
                f'</div></div>')
