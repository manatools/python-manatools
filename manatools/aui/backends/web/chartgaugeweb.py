"""
Web backend ChartGauge implementation.

The dial is generated server-side as inline SVG from YChartGaugeBase (angles,
ticks, band arcs, value arc): no script, no remote content.  The whole dial
is one focusable button carrying ``data-gauge``; manatools.js turns a click
(or Enter/Space) into an Activated event with ``data: {gauge: true}``,
routed by YDialogWeb to _handle_gauge_click().

The SVG uses a coordinate system centered on the dial (radius 100) whose
viewBox is the bounding box of everything drawn, scaled by CSS.  Text
widths are estimated (the server cannot measure fonts).

Author: Matteo Pasotti <xquiet@coriolite.com>

License: LGPLv2+
"""

import logging
import math

from ...yui_common import YChartGaugeBase, YChartLegendPosition
from .commonweb import escape_attr, escape_html, widget_attrs

logger = logging.getLogger("manatools.aui.web.YChartGaugeWeb")

# Radii in SVG user units (dial center at 0,0).
_R_BAND_OUT = 100.0     # thin band ring
_R_BAND_IN = 94.0
_R_TRACK_OUT = 90.0     # thick track / value ring
_R_TRACK_IN = 70.0
_R_LABEL = 108.0        # tick labels, outside the dial
_TICK_FONT = 10.0
_VALUE_FONT = 28.0
_SUBTITLE_FONT = 11.0
_CHAR_W = 0.6           # estimated glyph width in em
_MIN_SWEEP = 0.01       # degrees: thinner arcs are not drawn


def _num(v: float) -> str:
    return f"{v:.3f}".rstrip("0").rstrip(".") or "0"


def _xy(angle_deg: float, radius: float):
    """Point at *angle_deg* (0 = 12 o'clock, clockwise) and *radius*."""
    a = math.radians(angle_deg)
    return radius * math.sin(a), -radius * math.cos(a)


def _pt(angle_deg: float, radius: float) -> str:
    x, y = _xy(angle_deg, radius)
    return f"{_num(x)},{_num(y)}"


def _arc_path(a0: float, a1: float, outer: float, inner: float) -> str:
    """Annular sector from *a0* to *a1* (a1 - a0 <= 300 degrees)."""
    large = 1 if a1 - a0 > 180.0 else 0
    ro, ri = _num(outer), _num(inner)
    return (f"M{_pt(a0, outer)} A{ro},{ro} 0 {large} 1 {_pt(a1, outer)} "
            f"L{_pt(a1, inner)} A{ri},{ri} 0 {large} 0 {_pt(a0, inner)} Z")


def _text_width(text: str, size: float) -> float:
    return len(text) * size * _CHAR_W


class YChartGaugeWeb(YChartGaugeBase):
    """Gauge (radial dial) rendered as inline SVG plus an HTML legend."""

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

    def _handle_gauge_click(self, payload) -> bool:
        """Browser reported a click / Enter on the dial (untrusted input)."""
        if payload is not True or not self.visible():
            return False
        return self._gauge_clicked()

    # -- rendering ----------------------------------------------------------

    def _text_layout(self):
        """``(value_y, value_size, subtitle_y)`` for the value block, or
        Nones for hidden parts.  Centered in the dial; below the hub when a
        needle is drawn; above the baseline for flat (near half circle) dials."""
        value = self._value_text() if self._show_value else ""
        size = _VALUE_FONT
        if value:
            size = max(10.0, min(_VALUE_FONT, 2 * _R_TRACK_IN * 0.85 / (len(value) * _CHAR_W)))
        sub = self._subtitle
        place = self._text_placement()
        value_y = sub_y = None
        if place == "below":
            y = 14.0
            if value:
                value_y = y + size / 2
                y += size + 2
            if sub:
                sub_y = y + _SUBTITLE_FONT / 2
        elif place == "above":
            y = -6.0
            if sub:
                sub_y = y - _SUBTITLE_FONT / 2
                y -= _SUBTITLE_FONT + 4
            if value:
                value_y = y - size / 2
        else:
            if value and sub:
                value_y, sub_y = -_SUBTITLE_FONT / 2 - 1, size / 2 + 2
            elif value:
                value_y = 0.0
            elif sub:
                sub_y = 0.0
        return value_y, size, sub_y

    def _render_svg(self) -> str:
        half = self._sweep / 2.0
        # Bounding box, grown by every element drawn.
        box = [-_R_BAND_OUT, -_R_BAND_OUT, _R_BAND_OUT,
               max(_R_BAND_OUT * self._dial_extent(), 8.0)]

        def grow(x0, y0, x1, y1):
            box[0], box[1] = min(box[0], x0), min(box[1], y0)
            box[2], box[3] = max(box[2], x1), max(box[3], y1)

        tip = self._tooltip()
        body = [f'<title>{escape_html(tip)}</title>',
                f'<path class="mana-chartgauge-track" d="{_arc_path(-half, half, _R_TRACK_OUT, _R_TRACK_IN)}"/>']
        for index, a0, a1, color in self._band_arcs():
            if a1 - a0 >= _MIN_SWEEP:
                body.append(f'<path class="mana-chartgauge-band" data-band="{index}"'
                            f' fill="{escape_attr(color)}"'
                            f' d="{_arc_path(a0, a1, _R_BAND_OUT, _R_BAND_IN)}"/>')
        a0, a1, color = self._value_arc()
        if a1 - a0 >= _MIN_SWEEP:
            body.append(f'<path class="mana-chartgauge-value" fill="{escape_attr(color)}"'
                        f' d="{_arc_path(a0, a1, _R_TRACK_OUT, _R_TRACK_IN)}"/>')
        if self._show_ticks:
            for _, angle, text in self._ticks():
                body.append(f'<line class="mana-chartgauge-tick" x1="{_num(_xy(angle, _R_TRACK_OUT)[0])}"'
                            f' y1="{_num(_xy(angle, _R_TRACK_OUT)[1])}"'
                            f' x2="{_num(_xy(angle, _R_BAND_OUT)[0])}"'
                            f' y2="{_num(_xy(angle, _R_BAND_OUT)[1])}"/>')
                x, y = _xy(angle, _R_LABEL)
                w = _text_width(text, _TICK_FONT)
                s = math.sin(math.radians(angle))
                anchor, x0 = ("start", x) if s > 0.3 else ("end", x - w) if s < -0.3 else ("middle", x - w / 2)
                grow(x0, y - _TICK_FONT * 0.6, x0 + w, y + _TICK_FONT * 0.6)
                body.append(f'<text class="mana-chartgauge-ticklabel" x="{_num(x)}" y="{_num(y)}"'
                            f' text-anchor="{anchor}" dominant-baseline="middle">{escape_html(text)}</text>')
        target = self._target_angle()
        if target is not None:
            x1, y1 = _xy(target, _R_TRACK_IN - 4)
            x2, y2 = _xy(target, _R_BAND_OUT + 2)
            grow(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            body.append(f'<line class="mana-chartgauge-target" x1="{_num(x1)}" y1="{_num(y1)}"'
                        f' x2="{_num(x2)}" y2="{_num(y2)}"/>')
        if self._show_needle:
            angle = self._angle_of(self._value)
            body.append(f'<path class="mana-chartgauge-needle" d="M{_pt(angle, _R_TRACK_OUT - 2)}'
                        f' L{_pt(angle + 90, 4)} L{_pt(angle + 180, 8)} L{_pt(angle - 90, 4)} Z"/>'
                        f'<circle class="mana-chartgauge-hub" r="6"/>')
            grow(-8, -8, 8, 8)
        value_y, size, sub_y = self._text_layout()
        if value_y is not None:
            text = self._value_text()
            w = _text_width(text, size)
            grow(-w / 2, value_y - size / 2, w / 2, value_y + size / 2)
            body.append(f'<text class="mana-chartgauge-valuetext" y="{_num(value_y)}"'
                        f' font-size="{_num(size)}" text-anchor="middle"'
                        f' dominant-baseline="middle">{escape_html(text)}</text>')
        if sub_y is not None:
            w = _text_width(self._subtitle, _SUBTITLE_FONT)
            grow(-w / 2, sub_y - _SUBTITLE_FONT / 2, w / 2, sub_y + _SUBTITLE_FONT / 2)
            body.append(f'<text class="mana-chartgauge-subtitle" y="{_num(sub_y)}"'
                        f' font-size="{_num(_SUBTITLE_FONT)}" text-anchor="middle"'
                        f' dominant-baseline="middle">{escape_html(self._subtitle)}</text>')
        x0, y0 = box[0] - 2, box[1] - 2
        w, h = box[2] - box[0] + 4, box[3] - box[1] + 4
        head = (f'<svg class="mana-chartgauge-svg" viewBox="{_num(x0)} {_num(y0)} {_num(w)} {_num(h)}"'
                f' data-gauge="1" tabindex="0" role="button" aria-label="{escape_attr(tip)}">')
        return head + "".join(body) + "</svg>"

    def _render_legend(self) -> str:
        if self._legend_position == YChartLegendPosition.Hidden:
            return ""
        rows = []
        for index, label, range_text, color in self._legend_rows():
            rows.append(
                f'<li class="mana-chartgauge-legend-row" data-band="{index}">'
                f'<svg class="mana-chartgauge-swatch" viewBox="0 0 10 10" aria-hidden="true">'
                f'<rect width="10" height="10" rx="2" fill="{escape_attr(color)}"/></svg>'
                f'<span class="mana-chartgauge-legend-label">{escape_html(label)}</span>'
                f'<span class="mana-chartgauge-legend-range">{escape_html(range_text)}</span></li>')
        return f'<ul class="mana-chartgauge-legend">{"".join(rows)}</ul>' if rows else ""

    def render(self) -> str:
        extra = ["mana-chartgauge-legend-" + self._legend_position.name.lower()]
        if not self._enabled:
            extra.append("mana-disabled")
        attrs = widget_attrs(self.id(), "YChartGauge", True, self._visible,
                             " ".join(extra),
                             extra_attrs={"title": self.helpText() or None})
        title = (f'<div class="mana-chartgauge-title">{escape_html(self._label)}</div>'
                 if self._label else "")
        try:
            body = (f'<div class="mana-chartgauge-dial">{self._render_svg()}</div>'
                    f'{self._render_legend()}')
        except Exception:
            # Never let one chart break the whole dialog page.
            logger.exception("YChartGauge render failed")
            body = '<div class="mana-chart-error">Chart unavailable</div>'
        return (f'<div {attrs}>{title}'
                f'<div class="mana-chartgauge-body">{body}</div></div>')
