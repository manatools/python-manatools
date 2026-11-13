# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
GTK4 backend YChartPie.

A Gtk.DrawingArea painted with cairo + PangoCairo: optional title, pie or
donut, legend on the right or at the bottom.  The model, the geometry and the
hit test come from YChartPieBase; this module only lays out, paints and maps
input to _slice_clicked().

Slice separators are cut out of the pie (cairo DEST_OUT inside a group), so
they show the real background whatever the theme.

Mouse: click on a slice or legend row activates it; hovering shows the slice
tooltip (else the widget help text).  Keyboard: arrows move the selection,
Enter/Space activate the selected slice.

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
import cairo
from ...yui_common import *

_GAP = 8            # pixels between pie, legend and title
_ROW_PAD = 4        # extra height of a legend row over the text height
_MIN_PIE = 64       # smallest pie diameter worth drawing
_PIE_HINT = 200     # natural pie diameter
_NO_DATA = "No data"


def _rgb(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) / 255.0 for i in (1, 3, 5))


class _PieArea(Gtk.DrawingArea):
    """Paints a YChartPieGtk and reports input back to it."""

    def __init__(self, owner):
        super().__init__()
        self._owner = weakref.ref(owner)
        # Layout of the last draw, used for hit testing.
        self._center = (0.0, 0.0)
        self._radius = 0.0
        self._row_rects = []        # [((x, y, w, h), slice index)]

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

    def _layout_for(self, text, bold=False):
        layout = self.create_pango_layout(text)
        if bold:
            attrs = Pango.AttrList()
            attrs.insert(Pango.attr_weight_new(Pango.Weight.BOLD))
            layout.set_attributes(attrs)
        return layout

    def _text_size(self, text, bold=False):
        """Pixel size of *text*, cached per font: creating a Pango layout for
        every measurement made large charts slow."""
        font = self.get_pango_context().get_font_description()
        font_key = font.to_string() if font is not None else ""
        cache = getattr(self, "_size_cache", None)
        if cache is None or cache[0] != font_key or len(cache[1]) > 20000:
            cache = self._size_cache = (font_key, {})
        key = (text, bold)
        size = cache[1].get(key)
        if size is None:
            size = cache[1][key] = self._layout_for(text, bold).get_pixel_size()
        return size

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

    def _legend_metrics(self, owner):
        """(row height, swatch, value col width, pct col width, label width);
        cached until the data, the percent column or the font changes."""
        key = (owner._version, owner.showPercent(), getattr(self, "_size_cache", ("",))[0])
        cached = getattr(self, "_metrics_cache", None)
        if cached is not None and cached[0] == key:
            return cached[1]
        metrics = self._measure_legend(owner)
        # The font key may only be known after the first measurement.
        self._metrics_cache = ((owner._version, owner.showPercent(), self._size_cache[0]), metrics)
        return metrics

    def _measure_legend(self, owner):
        text_h = self._text_size("Ag")[1]
        row_h = text_h + _ROW_PAD
        swatch = max(8, int(text_h * 0.8))
        rows = owner._legend_rows()
        value_w = max((self._text_size(r[2])[0] for r in rows), default=0)
        pct_w = self._text_size("100.0%")[0] if owner.showPercent() else 0
        label_w = max((self._text_size(r[1])[0] for r in rows), default=0)
        return row_h, swatch, value_w, pct_w, label_w

    def _legend_width(self, owner):
        _row_h, swatch, value_w, pct_w, label_w = self._legend_metrics(owner)
        w = 2 + swatch + _GAP + label_w + _GAP + value_w + 2
        if pct_w:
            w += _GAP + pct_w
        return w

    def _title_height(self, owner):
        return (self._text_size(owner.label(), True)[1] + _GAP) if owner.label() else 0

    def update_size_request(self):
        owner = self._owner()
        if owner is None:
            return
        title_h = self._title_height(owner)
        pos = owner.legendPosition()
        w = h = _PIE_HINT
        if pos != YChartLegendPosition.Hidden and owner.sliceCount() > 0:
            row_h = self._legend_metrics(owner)[0]
            legend_w = min(self._legend_width(owner), 320)
            legend_h = min(owner.sliceCount(), 12) * row_h
            if pos == YChartLegendPosition.Bottom:
                w, h = max(_PIE_HINT, legend_w), _PIE_HINT + _GAP + legend_h
            else:
                w, h = _PIE_HINT + _GAP + legend_w, max(_PIE_HINT, legend_h)
        # Natural size; the minimum stays small so the chart can shrink.
        self.set_content_width(int(w))
        self.set_content_height(int(h + title_h))
        self.set_size_request(_MIN_PIE * 2, _MIN_PIE + title_h)

    # -- layout -------------------------------------------------------------

    def _layout(self, owner, width, height):
        """(title rect, pie (cx, cy, radius), legend rect); rects are (x, y, w, h)."""
        x, y, w, h = 2.0, 2.0, max(0.0, width - 4.0), max(0.0, height - 4.0)
        title = None
        if owner.label():
            th = self._text_size(owner.label(), True)[1]
            title = (x, y, w, th)
            y += th + _GAP
            h = max(0.0, h - th - _GAP)

        legend = None
        pos = owner.legendPosition()
        if pos != YChartLegendPosition.Hidden and owner.sliceCount() > 0:
            if pos == YChartLegendPosition.Right:
                lw = min(self._legend_width(owner), max(w - _MIN_PIE - _GAP, w * 0.5))
                legend = (x + w - lw, y, lw, h)
                w = max(0.0, w - lw - _GAP)
            else:
                row_h = self._legend_metrics(owner)[0]
                lh = min(owner.sliceCount() * row_h, max(h - _MIN_PIE - _GAP, h * 0.4))
                lw = min(self._legend_width(owner), w)
                legend = (x + (w - lw) / 2.0, y + h - lh, lw, lh)
                h = max(0.0, h - lh - _GAP)

        radius = max(0.0, min(w, h) / 2.0)
        return title, (x + w / 2.0, y + h / 2.0, radius), legend

    # -- painting -----------------------------------------------------------

    @staticmethod
    def _sector(cr, cx, cy, r_out, r_in, start, sweep):
        """Add a slice path; angles as in YChartPieBase (0 = 12 o'clock, clockwise)."""
        if sweep >= 359.999:
            cr.new_sub_path()
            cr.arc(cx, cy, r_out, 0, 2 * math.pi)
            if r_in > 0:
                cr.new_sub_path()
                cr.arc_negative(cx, cy, r_in, 2 * math.pi, 0)
            cr.close_path()
            return
        a0 = math.radians(start - 90.0)     # cairo: 0 = 3 o'clock, clockwise
        a1 = math.radians(start + sweep - 90.0)
        if r_in > 0:
            cr.new_sub_path()
            cr.arc(cx, cy, r_out, a0, a1)
            cr.arc_negative(cx, cy, r_in, a1, a0)
        else:
            cr.move_to(cx, cy)
            cr.arc(cx, cy, r_out, a0, a1)
        cr.close_path()

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
        alpha = 1.0 if self.is_sensitive() else 0.5
        if alpha < 1.0:
            cr.push_group()

        title, (cx, cy, radius), legend = self._layout(owner, width, height)
        self._center = (cx, cy)
        self._radius = radius

        if title is not None:
            layout = self._layout_for(owner.label(), True)
            layout.set_width(int(title[2] * Pango.SCALE))
            layout.set_ellipsize(Pango.EllipsizeMode.END)
            cr.set_source_rgba(*fg)
            cr.move_to(title[0], title[1])
            PangoCairo.show_layout(cr, layout)

        r_in = radius * owner.donutRatio()
        geom = owner._geometry()
        if radius >= 2:
            if not geom:
                cr.set_source_rgba(fg[0], fg[1], fg[2], 0.25)
                self._sector(cr, cx, cy, radius, r_in or radius * 0.6, 0, 360)
                cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
                cr.fill()
                self._center_text(cr, _NO_DATA, cx, cy, radius * 1.2, fg)
            else:
                cr.push_group()
                cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
                # Slices thinner than a pixel along the rim are invisible on
                # their own: each run of them is filled as one wedge (color of
                # its first slice).  Hit testing still uses the real slices.
                deg_px = 360.0 / max(1e-9, 2 * math.pi * radius)
                sectors = []        # (start, sweep, color) actually drawn
                run = None
                for _index, start, sweep, color in geom:
                    if sweep < deg_px:
                        if run is None:
                            run = [start, sweep, color]
                        else:
                            run[1] += sweep
                        if run[1] >= deg_px:
                            sectors.append(tuple(run))
                            run = None
                        continue
                    if run is not None:
                        sectors.append(tuple(run))
                        run = None
                    sectors.append((start, sweep, color))
                if run is not None:
                    sectors.append(tuple(run))
                for start, sweep, color in sectors:
                    cr.set_source_rgb(*_rgb(color))
                    self._sector(cr, cx, cy, radius, r_in, start, sweep)
                    cr.fill()
                if len(sectors) > 1:
                    # Cut 1px separators so the background shows between
                    # slices, only where they leave some slice visible.
                    cr.set_operator(cairo.OPERATOR_DEST_OUT)
                    cr.set_source_rgba(0, 0, 0, 1)
                    cr.set_line_width(1.0)
                    for start, sweep, _color in sectors:
                        if sweep >= 3 * deg_px:
                            self._sector(cr, cx, cy, radius, r_in, start, sweep)
                            cr.stroke()
                    cr.set_operator(cairo.OPERATOR_OVER)
                cr.pop_group_to_source()
                cr.paint()
                selected = owner.selectedSlice()
                for index, start, sweep, _color in geom:
                    if index == selected:
                        cr.set_source_rgba(*fg)
                        cr.set_line_width(2.5)
                        self._sector(cr, cx, cy, radius, r_in, start, sweep)
                        cr.stroke()
                if r_in > 0 and owner.centerText():
                    self._center_text(cr, owner.centerText(), cx, cy, r_in * 1.8, fg)

        self._paint_legend(cr, owner, legend, fg)

        if self.has_focus() and radius >= 2:
            cr.set_source_rgba(fg[0], fg[1], fg[2], 0.5)
            cr.set_line_width(1.0)
            cr.set_dash([2.0, 2.0])
            cr.rectangle(0.5, 0.5, width - 1, height - 1)
            cr.stroke()
            cr.set_dash([])

        if alpha < 1.0:
            cr.pop_group_to_source()
            cr.paint_with_alpha(alpha)

    def _center_text(self, cr, text, cx, cy, max_w, fg):
        layout = self._layout_for(text)
        layout.set_width(int(max(1, max_w) * Pango.SCALE))
        layout.set_ellipsize(Pango.EllipsizeMode.END)
        layout.set_alignment(Pango.Alignment.CENTER)
        _w, h = layout.get_pixel_size()
        cr.set_source_rgba(*fg)
        cr.move_to(cx - max_w / 2.0, cy - h / 2.0)
        PangoCairo.show_layout(cr, layout)

    def _paint_legend(self, cr, owner, rect, fg):
        self._row_rects = []
        if rect is None or rect[3] <= 0:
            return
        x0, y, lw, lh = rect
        row_h, swatch, value_w, pct_w, _label_w = self._legend_metrics(owner)
        rows = owner._legend_rows()
        fit = max(0, int(lh // row_h))
        hidden = 0
        if fit < len(rows):
            hidden = len(rows) - max(fit - 1, 0)
            rows = rows[:max(fit - 1, 0)]
        label_w = lw - 2 - swatch - _GAP - value_w - _GAP - 2 - ((_GAP + pct_w) if pct_w else 0)
        selected = owner.selectedSlice()
        for index, label, value_text, pct_text, color in rows:
            self._row_rects.append(((x0, y, lw, row_h), index))
            if index == selected:
                cr.set_source_rgba(fg[0], fg[1], fg[2], 0.15)
                cr.rectangle(x0, y, lw, row_h)
                cr.fill()
            cr.set_source_rgb(*_rgb(color))
            cr.rectangle(x0 + 2, y + (row_h - swatch) / 2.0, swatch, swatch)
            cr.fill()
            x = x0 + 2 + swatch + _GAP
            if label_w > 0:
                self._cell(cr, label, x, y, label_w, row_h, fg, Pango.Alignment.LEFT)
                x += label_w + _GAP
            self._cell(cr, value_text, x, y, value_w, row_h, fg, Pango.Alignment.RIGHT)
            x += value_w + _GAP
            if pct_w:
                self._cell(cr, pct_text, x, y, pct_w, row_h, fg, Pango.Alignment.RIGHT)
            y += row_h
        if hidden and fit > 0:
            self._cell(cr, f"… +{hidden}", x0 + 2, y, lw, row_h, fg, Pango.Alignment.LEFT)

    def _cell(self, cr, text, x, y, w, h, fg, align):
        layout = self._layout_for(text)
        layout.set_width(int(max(1, w) * Pango.SCALE))
        layout.set_ellipsize(Pango.EllipsizeMode.END)
        layout.set_alignment(align)
        th = layout.get_pixel_size()[1]
        cr.set_source_rgba(*fg)
        cr.move_to(x, y + (h - th) / 2.0)
        PangoCairo.show_layout(cr, layout)

    # -- input --------------------------------------------------------------

    def _index_at(self, owner, x, y) -> int:
        for (rx, ry, rw, rh), index in self._row_rects:
            if rx <= x < rx + rw and ry <= y < ry + rh:
                return index
        return owner._slice_at(x - self._center[0], y - self._center[1], self._radius)

    def _on_pressed(self, _gesture, _n_press, x, y):
        owner = self._owner()
        if owner is None:
            return
        self.grab_focus()
        index = self._index_at(owner, x, y)
        if index >= 0:
            owner._slice_clicked(index)

    def _on_motion(self, _controller, x, y):
        owner = self._owner()
        if owner is None:
            return
        self.set_cursor_from_name("pointer" if self._index_at(owner, x, y) >= 0 else None)

    def _on_key(self, _controller, keyval, _keycode, _state):
        owner = self._owner()
        count = owner.sliceCount() if owner is not None else 0
        if count == 0:
            return False
        current = owner.selectedSlice()
        if keyval in (Gdk.KEY_Right, Gdk.KEY_Down):
            owner.setSelectedSlice((current + 1) % count)
        elif keyval in (Gdk.KEY_Left, Gdk.KEY_Up):
            owner.setSelectedSlice((current - 1) % count if current >= 0 else count - 1)
        elif keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space) and current >= 0:
            owner._slice_clicked(current)
        else:
            return False
        return True

    def _on_query_tooltip(self, _widget, x, y, _keyboard_mode, tooltip):
        owner = self._owner()
        if owner is None:
            return False
        index = self._index_at(owner, x, y)
        text = owner._slice_tooltip(index) if index >= 0 else owner.helpText()
        if not text:
            return False
        tooltip.set_text(text)
        return True


class YChartPieGtk(YChartPieBase):
    """Pie / donut chart drawn on a Gtk.DrawingArea."""

    def __init__(self, parent=None, label: str = ""):
        # Attributes first: addChild() on the parent may build us immediately.
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        super().__init__(parent, label)

    def _create_backend_widget(self):
        area = _PieArea(self)
        self._backend_widget = area
        self._apply_size_policy()
        try:
            area.set_sensitive(bool(self._enabled))
            area.set_visible(self.visible())
            area.update_property([Gtk.AccessibleProperty.LABEL], [self._label or "Pie chart"])
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
        # Re-measuring is O(labels): do it once per burst of changes (e.g. an
        # addSlice() loop), when the main loop is idle.
        if not getattr(self, "_size_idle", 0):
            self._size_idle = GLib.idle_add(self._idle_update_size)

    def _idle_update_size(self):
        self._size_idle = 0
        area = getattr(self, "_backend_widget", None)
        if area is not None:
            try:
                area.update_size_request()
            except Exception:
                self._logger.exception("Failed to update size request")
        return False
        try:
            area.update_property([Gtk.AccessibleProperty.LABEL], [self._label or "Pie chart"])
        except Exception:
            self._logger.debug("accessible label update failed", exc_info=True)

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
        # Shown by _PieArea's query-tooltip when not over a slice.
        super().setHelpText(help_text)
