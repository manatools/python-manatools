# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
GTK4 backend YChartBar.

A Gtk.DrawingArea painted with cairo + PangoCairo: optional title, value
axis with tick labels and optional gridlines, category labels, bars (grouped
or stacked, vertical or horizontal), optional value labels and a series
legend on the right or at the bottom.  The model, the axis range, the bar
geometry and the hit test come from YChartBarBase; this module only lays
out with Pango metrics, paints and maps input to _bar_clicked().

Mouse: click on a bar activates it; hovering shows the bar tooltip (else the
widget help text).  Keyboard: arrows along the category axis move between
categories, the other two arrows between series; Enter/Space activate.

License: LGPLv2+

@package manatools.aui.backends.gtk
'''
import logging
import math
import weakref

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import GLib, Gtk, Gdk, Pango, PangoCairo
from ...yui_common import *
from .chartpiegtk import _rgb

_GAP = 6            # pixels between labels, axis, legend and title
_ROW_PAD = 4        # extra height of a legend row over the text height
_MIN_PLOT = 48      # smallest plot side worth drawing
_NO_DATA = "No data"
_MIN_LABEL_CHARS = 6


class _BarArea(Gtk.DrawingArea):
    """Paints a YChartBarGtk and reports input back to it."""

    def __init__(self, owner):
        super().__init__()
        self._owner = weakref.ref(owner)
        self._plot = None       # (left, top, right, bottom, horizontal, vmin, span) of last draw

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
            c = self.get_color() if hasattr(self, "get_color") else self.get_style_context().get_color()
            return (c.red, c.green, c.blue, c.alpha)
        except Exception:
            return (0.0, 0.0, 0.0, 1.0)

    def _text(self, cr, text, x, y, w, h, rgba, align=Pango.Alignment.LEFT, valign=0.5, bold=False):
        """Draw *text* ellipsized into the box (x, y, w, h)."""
        layout = self._layout_for(text, bold)
        layout.set_width(int(max(1, w) * Pango.SCALE))
        layout.set_ellipsize(Pango.EllipsizeMode.END)
        layout.set_alignment(align)
        th = layout.get_pixel_size()[1]
        cr.set_source_rgba(*rgba)
        cr.move_to(x, y + (h - th) * valign)
        PangoCairo.show_layout(cr, layout)

    def _halo_text(self, cr, text, x, y, w, h, align, valign):
        """White text with a dark halo, readable on any bar color."""
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            self._text(cr, text, x + dx, y + dy, w, h, (0, 0, 0, 0.45), align, valign)
        self._text(cr, text, x, y, w, h, (1, 1, 1, 1), align, valign)

    def _widest(self, owner, cat_texts):
        """Widest category label, cached until the data or the font changes."""
        key = (owner._version, getattr(self, "_size_cache", ("",))[0])
        cached = getattr(self, "_widest_cache", None)
        if cached is not None and cached[0] == key:
            return cached[1]
        widest = max((self._text_size(t)[0] for t in cat_texts), default=0)
        self._widest_cache = ((owner._version, self._size_cache[0]), widest)
        return widest

    # -- legend -------------------------------------------------------------

    def _legend_rows(self, owner):
        rows = owner._legend_rows()
        if owner.legendPosition() == YChartLegendPosition.Hidden or not any(r[1] for r in rows):
            return []
        return rows

    def _legend_size(self, owner):
        """(row height, swatch, width of the widest row, bold for the selection)."""
        text_h = self._text_size("Ag")[1]
        row_h = text_h + _ROW_PAD
        swatch = max(8, int(text_h * 0.8))
        widest = max((self._text_size(r[1], True)[0] for r in self._legend_rows(owner)), default=0)
        return row_h, swatch, 2 + swatch + _GAP + widest + 2

    # -- size ---------------------------------------------------------------

    def update_size_request(self):
        owner = self._owner()
        if owner is None:
            return
        fh = self._text_size("Ag")[1]
        n = max(1, owner.categoryCount())
        k = max(1, owner.seriesCount())
        per = (k if not owner.stacked() else 1) * 10 + 10
        if owner.orientation() == YChartBarOrientation.Horizontal:
            w, h = 320, max(160, n * max(per, fh + 4))
        else:
            w, h = max(240, n * per) + 40, 220
        w, h = min(w, 900), min(h, 600)
        rows = self._legend_rows(owner)
        if rows:
            row_h, _sw, legend_w = self._legend_size(owner)
            if owner.legendPosition() == YChartLegendPosition.Bottom:
                h += _GAP + row_h * min(len(rows), 4)
            else:
                w += _GAP + min(legend_w, 240)
        if owner.label():
            h += self._text_size(owner.label(), True)[1] + _GAP
        self.set_content_width(int(w))
        self.set_content_height(int(h))
        self.set_size_request(_MIN_PLOT * 3, _MIN_PLOT + 2 * fh)

    # -- layout -------------------------------------------------------------

    def _layout(self, owner, width, height):
        """(title box, plot area box, legend box); boxes are [x, y, w, h] or None."""
        x, y, w, h = 2.0, 2.0, max(0.0, width - 4.0), max(0.0, height - 4.0)
        title = None
        if owner.label():
            th = self._text_size(owner.label(), True)[1]
            title = (x, y, w, th)
            y += th + _GAP
            h = max(0.0, h - th - _GAP)
        legend = None
        rows = self._legend_rows(owner)
        if rows:
            row_h, _sw, legend_w = self._legend_size(owner)
            if owner.legendPosition() == YChartLegendPosition.Right:
                lw = min(legend_w, max(w - 2 * _MIN_PLOT - _GAP, w * 0.35))
                legend = (x + w - lw, y, lw, h)
                w = max(0.0, w - lw - _GAP)
            else:
                lh = min(len(rows) * row_h, max(h - _MIN_PLOT - _GAP, h * 0.3))
                lw = min(legend_w, w)
                legend = (x + (w - lw) / 2.0, y + h - lh, lw, lh)
                h = max(0.0, h - lh - _GAP)
        return title, (x, y, w, h), legend

    def _plot_box(self, owner, area, tick_texts, cat_texts):
        ax, ay, aw, ah = area
        fh = self._text_size("Ag")[1]
        values = owner.showValues() and not owner.stacked()
        if owner.orientation() == YChartBarOrientation.Horizontal:
            cat_w = self._widest(owner, cat_texts)
            left = ax + min(cat_w, aw * 0.35) + _GAP
            right = ax + aw - self._text_size(tick_texts[-1])[0] / 2.0 - 2
            top = ay + 2
            bottom = ay + ah - fh - _GAP
        else:
            tick_w = max(self._text_size(t)[0] for t in tick_texts)
            left = ax + tick_w + _GAP
            right = ax + aw - 2
            top = ay + fh / 2.0 + (fh if values else 0)
            bottom = ay + ah - fh - _GAP
        return left, top, right, bottom

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
        dim = not self.is_sensitive()
        if dim:
            cr.push_group()
        try:
            self._paint(cr, owner, width, height)
        finally:
            if dim:
                cr.pop_group_to_source()
                cr.paint_with_alpha(0.5)

    def _paint(self, cr, owner, width, height):
        fg = self._fg()
        muted = (fg[0], fg[1], fg[2], 0.65)
        gridc = (fg[0], fg[1], fg[2], 0.15)
        fh = self._text_size("Ag")[1]

        title, area, legend = self._layout(owner, width, height)
        if title is not None:
            self._text(cr, owner.label(), *title, fg, bold=True)
        self._paint_legend(cr, owner, legend, fg)

        horizontal = owner.orientation() == YChartBarOrientation.Horizontal
        vmin, vmax, ticks = owner._value_axis()
        span = (vmax - vmin) or 1.0
        tick_texts = [owner._format_tick(t) for t in ticks]
        n = owner.categoryCount()
        cat_texts = [owner.categoryLabel(c) for c in range(n)]
        left, top, right, bottom = self._plot_box(owner, area, tick_texts, cat_texts)
        if right - left < 8 or bottom - top < 8:
            self._plot = None
            return
        self._plot = (left, top, right, bottom, horizontal, vmin, span)
        pw, ph = right - left, bottom - top
        ax, ay, aw, ah = area

        def vpos(v):
            return (left + (v - vmin) / span * pw) if horizontal else (bottom - (v - vmin) / span * ph)

        def upos(u):
            return (top + u * ph) if horizontal else (left + u * pw)

        def line(x0, y0, x1, y1, rgba, w):
            cr.set_source_rgba(*rgba)
            cr.set_line_width(w)
            cr.move_to(x0, y0)
            cr.line_to(x1, y1)
            cr.stroke()

        # value axis: gridlines, zero line, tick labels
        for t, label in zip(ticks, tick_texts):
            pos = vpos(t)
            if t == 0 or owner.showGrid():
                rgba, lw = (muted, 1.0) if t == 0 else (gridc, 1.0)
                if horizontal:
                    line(pos, top, pos, bottom, rgba, lw)
                else:
                    line(left, pos, right, pos, rgba, lw)
            if horizontal:
                tw = self._text_size(label)[0]
                self._text(cr, label, pos - tw / 2.0 - 1, bottom + _GAP / 2.0, tw + 2, fh, muted,
                           Pango.Alignment.CENTER)
            else:
                self._text(cr, label, ax, pos - fh / 2.0, left - ax - _GAP / 2.0, fh, muted,
                           Pango.Alignment.RIGHT)
        if horizontal:
            line(left, bottom, right, bottom, muted, 1.0)
        else:
            line(left, top, left, bottom, muted, 1.0)

        if n == 0 or owner.seriesCount() == 0:
            tw, th = self._text_size(_NO_DATA)
            self._text(cr, _NO_DATA, left + (pw - tw) / 2.0, top + (ph - th) / 2.0, tw + 2, th, fg)
            return

        # category labels, thinned out when they would overlap
        slot = (ph if horizontal else pw) / n
        if horizontal:
            every = max(1, math.ceil(fh / slot))
            for c in range(0, n, every):
                mid = upos((c + 0.5) / n)
                self._text(cr, cat_texts[c], ax, mid - fh / 2.0, left - ax - _GAP, fh, fg,
                           Pango.Alignment.RIGHT)
        else:
            longest = self._widest(owner, cat_texts)
            want = min(longest, self._text_size("M" * _MIN_LABEL_CHARS)[0]) + 2 * _GAP
            every = max(1, math.ceil(want / slot))
            box_w = slot * every - 2 * _GAP
            last_end = -1e9
            for c in range(0, n, every):
                tw = min(self._text_size(cat_texts[c])[0], box_w)
                x = upos((c + 0.5) / n) - tw / 2.0
                x = max(ax, min(x, ax + aw - tw))       # keep inside the widget
                if x < last_end + _GAP:
                    continue                # pushed onto its neighbour by the edge
                last_end = x + tw
                self._text(cr, cat_texts[c], x, bottom + _GAP / 2.0, tw + 1, fh, fg)

        # bars
        selected = (owner.selectedCategory(), owner.selectedSeries())
        sel_rect = None
        values = []
        # Bars thinner than a pixel are merged per pixel line and color
        # (overlapping extents only), so dense charts fill at most a few
        # rectangles per pixel instead of one per bar.
        thin = {}           # (pixel, color) -> [[lo, hi], ...] along the value axis
        for c, s, u0, u1, v0, v1, color in owner._bar_geometry():
            a, b = upos(u0), upos(u1)
            q0, q1 = vpos(v0), vpos(v1)
            lo, hi = min(q0, q1), max(q0, q1)
            if horizontal:
                rect = (lo, a, max(hi - lo, 1.0), max(b - a, 1.0))
            else:
                rect = (a, lo, max(b - a, 1.0), max(hi - lo, 1.0))
            if (c, s) == selected:
                sel_rect = rect
            if b - a < 1.0:
                spans = thin.setdefault((int(a), color), [])
                if spans and lo <= spans[-1][1] + 1.0 and hi >= spans[-1][0] - 1.0:
                    spans[-1][0] = min(spans[-1][0], lo)
                    spans[-1][1] = max(spans[-1][1], hi)
                else:
                    spans.append([lo, hi])
                continue
            cr.set_source_rgb(*_rgb(color))
            cr.rectangle(*rect)
            cr.fill()
            if owner.showValues() and b - a >= 3.0:     # no room for labels on thinner bars
                values.append((c, s, rect, v1 >= v0))
        for (pixel, color), spans in thin.items():
            cr.set_source_rgb(*_rgb(color))
            for lo, hi in spans:
                if horizontal:
                    cr.rectangle(lo, pixel, max(hi - lo, 1.0), 1.0)
                else:
                    cr.rectangle(pixel, lo, 1.0, max(hi - lo, 1.0))
            cr.fill()
        if sel_rect is not None:
            cr.set_source_rgba(*fg)
            cr.set_line_width(2.0)
            cr.rectangle(*sel_rect)
            cr.stroke()

        # value labels: inside the segment when stacked, else past the bar end
        for c, s, (x, y, w, h), up in values:
            label = owner._value_text(c, s)
            tw = self._text_size(label)[0]
            if owner.stacked():
                if w < tw + 4 or h < fh:
                    continue
                self._halo_text(cr, label, x, y, w, h, Pango.Alignment.CENTER, 0.5)
            elif horizontal:
                if up and x + w + 2 + tw <= right:
                    self._text(cr, label, x + w + 2, y, tw + 2, h, fg)
                elif not up and x - 2 - tw >= left:
                    self._text(cr, label, x - 4 - tw, y, tw + 2, h, fg, Pango.Alignment.RIGHT)
                elif w >= tw + 4:
                    self._halo_text(cr, label, x + 2, y, w - 4, h,
                                    Pango.Alignment.RIGHT if up else Pango.Alignment.LEFT, 0.5)
            else:
                if up and y - fh >= ay:
                    self._text(cr, label, x + w / 2.0 - tw / 2.0 - 1, y - fh, tw + 2, fh, fg,
                               Pango.Alignment.CENTER)
                elif not up and y + h + fh <= bottom:
                    self._text(cr, label, x + w / 2.0 - tw / 2.0 - 1, y + h, tw + 2, fh, fg,
                               Pango.Alignment.CENTER)
                elif h >= fh:
                    # Centered on the bar but as wide as the text, so narrow
                    # bars do not ellipsize it.
                    self._halo_text(cr, label, x + w / 2.0 - tw / 2.0 - 1, y, tw + 2, h,
                                    Pango.Alignment.CENTER, 0.0 if up else 1.0)

        if self.has_focus():
            cr.set_source_rgba(fg[0], fg[1], fg[2], 0.5)
            cr.set_line_width(1.0)
            cr.set_dash([2.0, 2.0])
            cr.rectangle(0.5, 0.5, width - 1, height - 1)
            cr.stroke()
            cr.set_dash([])

    def _paint_legend(self, cr, owner, box, fg):
        if box is None or box[3] <= 0:
            return
        x0, y, lw, lh = box
        row_h, swatch, _w = self._legend_size(owner)
        rows = self._legend_rows(owner)
        fit = max(0, int(lh // row_h))
        hidden = 0
        if fit < len(rows):
            hidden = len(rows) - max(fit - 1, 0)
            rows = rows[:max(fit - 1, 0)]
        for s, name, color in rows:
            cr.set_source_rgb(*_rgb(color))
            cr.rectangle(x0 + 2, y + (row_h - swatch) / 2.0, swatch, swatch)
            cr.fill()
            tx = x0 + 2 + swatch + _GAP
            self._text(cr, name, tx, y, x0 + lw - tx, row_h, fg, bold=(s == owner.selectedSeries()))
            y += row_h
        if hidden and fit > 0:
            self._text(cr, f"… +{hidden}", x0 + 2, y, lw, row_h, fg)

    # -- input --------------------------------------------------------------

    def _bar_at_pos(self, owner, x, y):
        if self._plot is None:
            return -1, -1
        left, top, right, bottom, horizontal, vmin, span = self._plot
        if not (left <= x <= right and top <= y <= bottom):
            return -1, -1
        length = max(1.0, (bottom - top) if horizontal else (right - left))
        if horizontal:
            u = (y - top) / length
            v = vmin + (x - left) / max(1.0, right - left) * span
        else:
            u = (x - left) / length
            v = vmin + (bottom - y) / max(1.0, bottom - top) * span
        return owner._bar_at(u, v, 1.0 / length)       # one pixel of tolerance

    def _on_pressed(self, _gesture, _n_press, x, y):
        owner = self._owner()
        if owner is None:
            return
        self.grab_focus()
        c, s = self._bar_at_pos(owner, x, y)
        if c >= 0:
            owner._bar_clicked(c, s)

    def _on_motion(self, _controller, x, y):
        owner = self._owner()
        if owner is None:
            return
        self.set_cursor_from_name("pointer" if self._bar_at_pos(owner, x, y)[0] >= 0 else None)

    def _on_key(self, _controller, keyval, _keycode, _state):
        owner = self._owner()
        if owner is None or owner.categoryCount() == 0 or owner.seriesCount() == 0:
            return False
        n, k = owner.categoryCount(), owner.seriesCount()
        c, s = owner.selectedCategory(), owner.selectedSeries()
        if owner.orientation() == YChartBarOrientation.Horizontal:
            cat_next, cat_prev, ser_next, ser_prev = Gdk.KEY_Down, Gdk.KEY_Up, Gdk.KEY_Right, Gdk.KEY_Left
        else:
            cat_next, cat_prev, ser_next, ser_prev = Gdk.KEY_Right, Gdk.KEY_Left, Gdk.KEY_Up, Gdk.KEY_Down
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            if c < 0:
                return False        # nothing selected: let Enter reach the default button
            owner._bar_clicked(c, s)
            return True
        if keyval not in (cat_next, cat_prev, ser_next, ser_prev):
            return False
        if c < 0:
            c, s = 0, 0
        elif keyval == cat_next:
            c = min(n - 1, c + 1)
        elif keyval == cat_prev:
            c = max(0, c - 1)
        elif keyval == ser_next:
            s = min(k - 1, s + 1)
        else:
            s = max(0, s - 1)
        owner.setSelectedBar(c, s)
        return True

    def _on_query_tooltip(self, _widget, x, y, _keyboard_mode, tooltip):
        owner = self._owner()
        if owner is None:
            return False
        c, s = self._bar_at_pos(owner, x, y)
        text = owner._bar_tooltip(c, s) if c >= 0 else owner.helpText()
        if not text:
            return False
        tooltip.set_text(text)
        return True


class YChartBarGtk(YChartBarBase):
    """Bar chart drawn on a Gtk.DrawingArea."""

    def __init__(self, parent=None, label: str = ""):
        # Attributes first: addChild() on the parent may build us immediately.
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        super().__init__(parent, label)

    def _create_backend_widget(self):
        area = _BarArea(self)
        self._backend_widget = area
        self._apply_size_policy()
        try:
            area.set_sensitive(bool(self._enabled))
            area.set_visible(self.visible())
        except Exception:
            self._logger.exception("Failed to apply initial widget state")
        self._update_accessible()
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

    def _update_accessible(self):
        try:
            self._backend_widget.update_property([Gtk.AccessibleProperty.LABEL],
                                                 [self._label or "Bar chart"])
        except Exception:
            self._logger.debug("accessible label update failed", exc_info=True)

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
        self._update_accessible()

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
        # Shown by _BarArea's query-tooltip when not over a bar.
        super().setHelpText(help_text)
