# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
GTK4 backend YChartGauge.

A Gtk.DrawingArea painted with cairo + PangoCairo: optional title, the dial
(track, band ring, value arc, ticks with labels, target marker, optional
needle, value text and subtitle) and a legend of the labelled bands on the
right or at the bottom.  Angles, ticks, colors and the hit test come from
YChartGaugeBase; this module only lays out, paints and maps input to
_gauge_clicked().

Mouse: a click on the dial activates it; hovering the dial shows the value
tooltip (else the widget help text).  Keyboard: Enter/Space activate.

License: LGPLv2+

@package manatools.aui.backends.gtk
'''
import math
import weakref
import logging

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import GLib, Gtk, Gdk, Pango, PangoCairo
from ...yui_common import *
from .chartpiegtk import _rgb

_GAP = 8            # pixels between dial, legend and title
_ROW_PAD = 4        # extra height of a legend row over the text height
_MIN_DIAL = 48      # smallest dial radius worth laying out for
_DIAL_HINT = 100    # natural dial radius
# Ring radii as fractions of the dial radius.
_BAND_IN = 0.94
_TRACK_OUT = 0.90
_TRACK_IN = 0.70


def _ring(cr, cx, cy, r_out, r_in, a0, a1):
    """Add an annular sector path (degrees, 0 = 12 o'clock, clockwise)."""
    s = math.radians(a0 - 90.0)         # cairo: 0 = 3 o'clock, clockwise
    e = math.radians(a1 - 90.0)
    cr.new_sub_path()
    cr.arc(cx, cy, r_out, s, e)
    cr.arc_negative(cx, cy, r_in, e, s)
    cr.close_path()


def _polar(cx, cy, angle, radius):
    a = math.radians(angle)
    return cx + radius * math.sin(a), cy - radius * math.cos(a)


class _GaugeArea(Gtk.DrawingArea):
    """Paints a YChartGaugeGtk and reports input back to it."""

    def __init__(self, owner):
        super().__init__()
        self._owner = weakref.ref(owner)
        # Layout of the last draw, used for hit testing.
        self._center = (0.0, 0.0)
        self._radius = 0.0

        self.set_draw_func(self._on_draw)
        self.set_focusable(True)
        self.set_has_tooltip(True)
        self.connect("query-tooltip", self._on_query_tooltip)

        click = Gtk.GestureClick()
        click.set_button(Gdk.BUTTON_PRIMARY)
        click.connect("pressed", self._on_pressed)
        self.add_controller(click)

        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_motion)
        self.add_controller(motion)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)

    # -- text helpers -------------------------------------------------------

    def _layout_for(self, text, bold=False, scale=1.0, px=0):
        """Pango layout of *text*: bold, scaled from the widget font, or with
        an absolute pixel size *px*."""
        layout = self.create_pango_layout(text)
        attrs = Pango.AttrList()
        if bold:
            attrs.insert(Pango.attr_weight_new(Pango.Weight.BOLD))
        if px:
            attrs.insert(Pango.attr_size_new_absolute(int(px * Pango.SCALE)))
        elif scale != 1.0:
            attrs.insert(Pango.attr_scale_new(scale))
        layout.set_attributes(attrs)
        return layout

    def _text_size(self, text, bold=False, scale=1.0, px=0):
        return self._layout_for(text, bold, scale, px).get_pixel_size()

    def _fg(self):
        try:
            if hasattr(self, "get_color"):          # GTK >= 4.10
                c = self.get_color()
            else:
                c = self.get_style_context().get_color()
            return (c.red, c.green, c.blue, c.alpha)
        except Exception:
            return (0.0, 0.0, 0.0, 1.0)

    # -- size ---------------------------------------------------------------

    def _label_margins(self, owner):
        """(horizontal, vertical) room for tick labels around the dial."""
        if not owner.showTicks():
            return 2.0, 2.0
        sizes = [self._text_size(t, scale=0.85) for _, _, t in owner._ticks()]
        return max((w for w, _ in sizes), default=0) + 6.0, max((h for _, h in sizes), default=0) + 2.0

    def _legend_metrics(self, owner):
        """(rows, row height, swatch, label width, range width)."""
        rows = owner._legend_rows()
        text_h = self._text_size("Ag")[1]
        row_h = text_h + _ROW_PAD
        swatch = max(8, int(text_h * 0.8))
        label_w = max((self._text_size(r[1])[0] for r in rows), default=0)
        range_w = max((self._text_size(r[2])[0] for r in rows), default=0)
        return rows, row_h, swatch, label_w, range_w

    def _legend_width(self, owner):
        _rows, _row_h, swatch, label_w, range_w = self._legend_metrics(owner)
        return 2 + swatch + _GAP + label_w + _GAP + range_w + 2

    def _has_legend(self, owner):
        return owner.legendPosition() != YChartLegendPosition.Hidden and bool(owner._legend_rows())

    def _title_height(self, owner):
        return (self._text_size(owner.label(), True)[1] + _GAP) if owner.label() else 0

    def _below(self, owner):
        """How far (in radii) the dial content reaches under the center."""
        below = max(owner._dial_extent(), 0.12)
        if owner._text_placement() == "below":
            below = max(below, 0.44)
        return below

    def _dial_size(self, owner, radius):
        mx, my = self._label_margins(owner)
        return 2 * (radius + mx), radius * (1 + self._below(owner)) + 2 * my

    def update_size_request(self):
        owner = self._owner()
        if owner is None:
            return
        title_h = self._title_height(owner)
        w, h = self._dial_size(owner, _DIAL_HINT)
        if self._has_legend(owner):
            rows, row_h = self._legend_metrics(owner)[:2]
            legend_w = min(self._legend_width(owner), 320)
            legend_h = min(len(rows), 8) * row_h
            if owner.legendPosition() == YChartLegendPosition.Bottom:
                w, h = max(w, legend_w), h + _GAP + legend_h
            else:
                w, h = w + _GAP + legend_w, max(h, legend_h)
        # Natural size; the minimum stays small so the gauge can shrink.
        self.set_content_width(int(w))
        self.set_content_height(int(h + title_h))
        mw, mh = self._dial_size(owner, _MIN_DIAL)
        self.set_size_request(int(mw), int(mh + title_h))

    # -- layout -------------------------------------------------------------

    def _layout(self, owner, width, height):
        """(title rect, dial rect, legend rect); rects are (x, y, w, h)."""
        x, y, w, h = 2.0, 2.0, max(0.0, width - 4.0), max(0.0, height - 4.0)
        title = None
        if owner.label():
            th = self._text_size(owner.label(), True)[1]
            title = (x, y, w, th)
            y += th + _GAP
            h = max(0.0, h - th - _GAP)
        legend = None
        if self._has_legend(owner):
            rows, row_h = self._legend_metrics(owner)[:2]
            min_w, min_h = self._dial_size(owner, _MIN_DIAL)
            if owner.legendPosition() == YChartLegendPosition.Right:
                lw = min(self._legend_width(owner), max(w - min_w - _GAP, w * 0.4))
                lh = min(h, len(rows) * row_h)
                legend = (x + w - lw, y + (h - lh) / 2.0, lw, lh)
                w = max(0.0, w - lw - _GAP)
            else:
                lh = min(len(rows) * row_h, max(h - min_h - _GAP, h * 0.4))
                lw = min(self._legend_width(owner), w)
                legend = (x + (w - lw) / 2.0, y + h - lh, lw, lh)
                h = max(0.0, h - lh - _GAP)
        return title, (x, y, w, h), legend

    def _fit_dial(self, owner, rect):
        """(cx, cy, radius) of the dial inside *rect*, label margins kept."""
        x, y, w, h = rect
        mx, my = self._label_margins(owner)
        w, h = max(0.0, w - 2 * mx), max(0.0, h - 2 * my)
        below = None
        if owner._text_placement() == "below":
            # Hub, value text (about 0.34 r) and the subtitle line under the center.
            below = 0.1 + (0.34 if owner.showValue() else 0.0)
            if owner.subtitle():
                h = max(0.0, h - self._text_size(owner.subtitle())[1])
        cx, cy, r = owner._dial_fit(w, h, below)
        return x + mx + cx, y + my + cy, r

    # -- painting -----------------------------------------------------------

    def _on_draw(self, _area, cr, width, height):
        owner = self._owner()
        if owner is None:
            return
        try:
            self.paint(cr, owner, width, height)
        except Exception:
            owner._logger.exception("draw failed")

    def paint(self, cr, owner, width, height):
        fg = self._fg()
        dim = (fg[0], fg[1], fg[2], fg[3] * 0.7)
        alpha = 1.0 if self.is_sensitive() else 0.5
        if alpha < 1.0:
            cr.push_group()

        title, dial, legend = self._layout(owner, width, height)
        if title is not None:
            layout = self._layout_for(owner.label(), True)
            layout.set_width(int(title[2] * Pango.SCALE))
            layout.set_ellipsize(Pango.EllipsizeMode.END)
            cr.set_source_rgba(*fg)
            cr.move_to(title[0], title[1])
            PangoCairo.show_layout(cr, layout)

        cx, cy, r = self._fit_dial(owner, dial)
        self._center, self._radius = (cx, cy), r
        if r >= 8:
            self._paint_dial(cr, owner, cx, cy, r, fg, dim)
        self._paint_legend(cr, owner, legend, fg, dim)

        if self.has_focus():
            cr.set_source_rgba(fg[0], fg[1], fg[2], 0.5)
            cr.set_line_width(1.0)
            cr.set_dash([2.0, 2.0])
            cr.rectangle(0.5, 0.5, width - 1, height - 1)
            cr.stroke()
            cr.set_dash([])

        if alpha < 1.0:
            cr.pop_group_to_source()
            cr.paint_with_alpha(alpha)

    def _paint_dial(self, cr, owner, cx, cy, r, fg, dim):
        half = owner.sweepAngle() / 2.0
        min_arc = 0.25 * 360.0 / max(1e-9, 2 * math.pi * r)    # quarter pixel
        cr.set_source_rgba(fg[0], fg[1], fg[2], 0.18)
        _ring(cr, cx, cy, r * _TRACK_OUT, r * _TRACK_IN, -half, half)
        cr.fill()
        for _i, a0, a1, color in owner._band_arcs():
            if a1 - a0 >= min_arc:
                cr.set_source_rgb(*_rgb(color))
                _ring(cr, cx, cy, r, r * _BAND_IN, a0, a1)
                cr.fill()
        a0, a1, color = owner._value_arc()
        if a1 - a0 >= min_arc:
            cr.set_source_rgb(*_rgb(color))
            _ring(cr, cx, cy, r * _TRACK_OUT, r * _TRACK_IN, a0, a1)
            cr.fill()

        if owner.showTicks():
            cr.set_line_width(1.0)
            for _v, angle, text in owner._ticks():
                cr.set_source_rgba(*dim)
                cr.move_to(*_polar(cx, cy, angle, r * _TRACK_OUT))
                cr.line_to(*_polar(cx, cy, angle, r))
                cr.stroke()
                # Label box pushed outward from the rim by half its size.
                layout = self._layout_for(text, scale=0.85)
                w, h = layout.get_pixel_size()
                px, py = _polar(cx, cy, angle, r + 3)
                a = math.radians(angle)
                cr.move_to(px + math.sin(a) * w / 2.0 - w / 2.0, py - math.cos(a) * h / 2.0 - h / 2.0)
                PangoCairo.show_layout(cr, layout)

        target = owner._target_angle()
        if target is not None:
            cr.set_source_rgba(*fg)
            cr.set_line_width(max(2.0, r * 0.03))
            cr.set_line_cap(1)          # cairo.LINE_CAP_ROUND
            cr.move_to(*_polar(cx, cy, target, r * _TRACK_IN - 4))
            cr.line_to(*_polar(cx, cy, target, r + 2))
            cr.stroke()
            cr.set_line_cap(0)

        if owner.showNeedle():
            angle = owner._angle_of(owner.value())
            hub = max(3.0, r * 0.06)
            cr.set_source_rgba(*fg)
            cr.move_to(*_polar(cx, cy, angle, r * _TRACK_OUT - 2))
            cr.line_to(*_polar(cx, cy, angle + 90, hub * 0.7))
            cr.line_to(*_polar(cx, cy, angle + 180, hub * 1.4))
            cr.line_to(*_polar(cx, cy, angle - 90, hub * 0.7))
            cr.close_path()
            cr.fill()
            cr.arc(cx, cy, hub, 0, 2 * math.pi)
            cr.fill()

        self._paint_text(cr, owner, cx, cy, r, fg, dim)

    def _paint_text(self, cr, owner, cx, cy, r, fg, dim):
        value = owner._value_text() if owner.showValue() else ""
        sub = owner.subtitle()
        if not value and not sub:
            return
        room = 2 * r * _TRACK_IN * 0.85
        vlayout = None
        vh = sh = 0
        if value:
            px = max(10, int(r * 0.28))
            vw = self._text_size(value, True, px=px)[0]
            if vw > room:
                px = max(10, int(px * room / vw))
            vlayout = self._layout_for(value, True, px=px)
            vlayout.set_width(int(room * Pango.SCALE))
            vlayout.set_ellipsize(Pango.EllipsizeMode.END)
            vlayout.set_alignment(Pango.Alignment.CENTER)
            vh = vlayout.get_pixel_size()[1]
        slayout = None
        if sub:
            slayout = self._layout_for(sub)
            slayout.set_width(int(room * Pango.SCALE))
            slayout.set_ellipsize(Pango.EllipsizeMode.END)
            slayout.set_alignment(Pango.Alignment.CENTER)
            sh = slayout.get_pixel_size()[1]
        place = owner._text_placement()
        if place == "below":
            top = cy + max(3.0, r * 0.06) * 1.6
        elif place == "above":
            top = cy - 4 - vh - sh
        else:
            top = cy - (vh + sh) / 2.0
        if vlayout is not None:
            cr.set_source_rgba(*fg)
            cr.move_to(cx - room / 2.0, top)
            PangoCairo.show_layout(cr, vlayout)
            top += vh
        if slayout is not None:
            cr.set_source_rgba(*dim)
            cr.move_to(cx - room / 2.0, top)
            PangoCairo.show_layout(cr, slayout)

    def _paint_legend(self, cr, owner, rect, fg, dim):
        if rect is None or rect[3] <= 0:
            return
        x0, y, lw, lh = rect
        rows, row_h, swatch, _label_w, range_w = self._legend_metrics(owner)
        fit = max(0, int(lh // row_h))
        label_w = lw - 2 - swatch - _GAP - range_w - _GAP - 2
        for _index, label, range_text, color in rows[:fit]:
            cr.set_source_rgb(*_rgb(color))
            cr.rectangle(x0 + 2, y + (row_h - swatch) / 2.0, swatch, swatch)
            cr.fill()
            x = x0 + 2 + swatch + _GAP
            if label_w > 0:
                self._cell(cr, label, x, y, label_w, row_h, fg, Pango.Alignment.LEFT)
                x += label_w + _GAP
            self._cell(cr, range_text, x, y, range_w, row_h, dim, Pango.Alignment.RIGHT)
            y += row_h

    def _cell(self, cr, text, x, y, w, h, color, align):
        layout = self._layout_for(text)
        layout.set_width(int(max(1, w) * Pango.SCALE))
        layout.set_ellipsize(Pango.EllipsizeMode.END)
        layout.set_alignment(align)
        th = layout.get_pixel_size()[1]
        cr.set_source_rgba(*color)
        cr.move_to(x, y + (h - th) / 2.0)
        PangoCairo.show_layout(cr, layout)

    # -- input --------------------------------------------------------------

    def _on_dial(self, owner, x, y) -> bool:
        return self._radius > 0 and owner._dial_hit(x - self._center[0], y - self._center[1], self._radius)

    def _on_pressed(self, _gesture, _n_press, x, y):
        owner = self._owner()
        if owner is None:
            return
        self.grab_focus()
        if self._on_dial(owner, x, y):
            owner._gauge_clicked()

    def _on_motion(self, _controller, x, y):
        owner = self._owner()
        if owner is None:
            return
        self.set_cursor_from_name("pointer" if self._on_dial(owner, x, y) else None)

    def _on_key(self, _controller, keyval, _keycode, _state):
        owner = self._owner()
        if owner is None or keyval not in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            return False
        owner._gauge_clicked()
        return True

    def _on_query_tooltip(self, _widget, x, y, _keyboard_mode, tooltip):
        owner = self._owner()
        if owner is None:
            return False
        text = owner._tooltip() if self._on_dial(owner, x, y) else owner.helpText()
        if not text:
            return False
        tooltip.set_text(text)
        return True


class YChartGaugeGtk(YChartGaugeBase):
    """Gauge (radial dial) drawn on a Gtk.DrawingArea."""

    def __init__(self, parent=None, label: str = ""):
        # Attributes first: addChild() on the parent may build us immediately.
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        super().__init__(parent, label)

    def _create_backend_widget(self):
        area = _GaugeArea(self)
        self._backend_widget = area
        self._apply_size_policy()
        try:
            area.set_sensitive(bool(self._enabled))
            area.set_visible(self.visible())
            area.update_property([Gtk.AccessibleProperty.LABEL], [self._label or "Gauge"])
        except Exception:
            self._logger.exception("Failed to apply initial widget state")
        area.update_size_request()
        self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())

    def _apply_size_policy(self):
        widget = getattr(self, "_backend_widget", None)
        if widget is None:
            return
        try:
            eff_h = bool(self.stretchable(YUIDimension.YD_HORIZ) or self.weight(YUIDimension.YD_HORIZ))
            eff_v = bool(self.stretchable(YUIDimension.YD_VERT) or self.weight(YUIDimension.YD_VERT))
            widget.set_hexpand(eff_h)
            widget.set_vexpand(eff_v)
            widget.set_halign(Gtk.Align.FILL if eff_h else Gtk.Align.START)
            widget.set_valign(Gtk.Align.FILL if eff_v else Gtk.Align.START)
        except Exception:
            self._logger.exception("_apply_size_policy failed")

    # -- backend hooks ------------------------------------------------------

    def _apply_chart(self):
        area = getattr(self, "_backend_widget", None)
        if area is None:
            return
        try:
            area.queue_draw()
        except Exception:
            self._logger.exception("Failed to redraw chart")
        # Measure once per burst of changes, when the main loop is idle.
        if not getattr(self, "_size_idle", 0):
            self._size_idle = GLib.idle_add(self._idle_update_size)

    def _idle_update_size(self):
        self._size_idle = 0
        area = getattr(self, "_backend_widget", None)
        if area is not None:
            try:
                area.update_size_request()
                area.update_property([Gtk.AccessibleProperty.LABEL], [self._label or "Gauge"])
            except Exception:
                self._logger.exception("Failed to update size request")
        return False

    # -- common widget API --------------------------------------------------

    def setStretchable(self, dimension, stretchable):
        super().setStretchable(dimension, stretchable)
        self._apply_size_policy()

    def _set_backend_enabled(self, enabled):
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.set_sensitive(bool(enabled))
        except Exception:
            self._logger.exception("Failed to set sensitive state")

    def setVisible(self, visible=True):
        super().setVisible(visible)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.set_visible(bool(visible))
        except Exception:
            self._logger.exception("setVisible failed")

    def setHelpText(self, help_text: str):
        # Shown by _GaugeArea's query-tooltip when not over the dial.
        super().setHelpText(help_text)
