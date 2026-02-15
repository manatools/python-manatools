# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.gtk contains all GTK backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
'''

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, GObject, GdkPixbuf, GLib
import cairo
import threading
import os
import logging
from ...yui_common import *


class _YHBoxMeasureBox(Gtk.Box):
    """Gtk.Box subclass delegating size requests to YHBoxGtk."""

    def __init__(self, owner):
        """Initialize the measuring box.

        Args:
            owner: Owning YHBoxGtk instance.
        """
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self._owner = owner

    def do_measure(self, orientation, for_size):
        """GTK4 virtual method for size measurement.

        Args:
            orientation: Gtk.Orientation (HORIZONTAL or VERTICAL)
            for_size: Size in the opposite orientation (-1 if not constrained)

        Returns:
            tuple: (minimum_size, natural_size, minimum_baseline, natural_baseline)
        """
        try:
            return self._owner.do_measure(orientation, for_size)
        except Exception:
            self._owner._logger.exception("HBox backend do_measure delegation failed", exc_info=True)
            return (0, 0, -1, -1)


class YHBoxGtk(YWidget):
    """Horizontal GTK4 container with weight-aware geometry management."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
    
    def widgetClass(self):
        return "YHBox"

    def stretchable(self, dim):
        for child in self._children:
            expand = bool(child.stretchable(dim))
            weight = bool(child.weight(dim))
            if expand or weight:
                return True
        return False

    def do_measure(self, orientation, for_size):
        """GTK4 virtual method for size measurement.

        Args:
            orientation: Gtk.Orientation (HORIZONTAL or VERTICAL)
            for_size: Size in the opposite orientation (-1 if not constrained)

        Returns:
            tuple: (minimum_size, natural_size, minimum_baseline, natural_baseline)
        """
        children = list(getattr(self, "_children", []) or [])
        if not children:
            return (0, 0, -1, -1)

        spacing = 5
        try:
            if getattr(self, "_backend_widget", None) is not None and hasattr(self._backend_widget, "get_spacing"):
                spacing = int(self._backend_widget.get_spacing())
        except Exception:
            self._logger.exception("Failed to read HBox spacing for measure", exc_info=True)
            spacing = 5

        minimum_size = 0
        natural_size = 0
        maxima_minimum = 0
        maxima_natural = 0

        for child in children:
            try:
                child_widget = child.get_backend_widget()
                cmin, cnat, _cbase_min, _cbase_nat = child_widget.measure(orientation, for_size)
            except Exception:
                self._logger.exception("HBox measure failed for child %s", getattr(child, "debugLabel", lambda: "<unknown>")(), exc_info=True)
                cmin, cnat = 0, 0

            if orientation == Gtk.Orientation.HORIZONTAL:
                minimum_size += int(cmin)
                natural_size += int(cnat)
            else:
                maxima_minimum = max(maxima_minimum, int(cmin))
                maxima_natural = max(maxima_natural, int(cnat))

        if orientation == Gtk.Orientation.HORIZONTAL:
            gap_total = max(0, len(children) - 1) * spacing
            minimum_size += gap_total
            natural_size += gap_total
        else:
            minimum_size = maxima_minimum
            natural_size = maxima_natural

        self._logger.debug(
            "HBox do_measure orientation=%s for_size=%s -> min=%s nat=%s",
            orientation,
            for_size,
            minimum_size,
            natural_size,
        )
        return (minimum_size, natural_size, -1, -1)

    def _create_backend_widget(self):
        """Create backend widget and configure weight/stretch behavior."""
        self._backend_widget = _YHBoxMeasureBox(self)

        # Collect children first so we can apply weight-based heuristics
        children = list(self._children)

        for child in children:
            try:
                self._logger.debug("HBox child: %s stretch(H)=%s weight(H)=%s stretch(V)=%s", child.widgetClass(), child.stretchable(YUIDimension.YD_HORIZ), child.weight(YUIDimension.YD_HORIZ), child.stretchable(YUIDimension.YD_VERT))
            except Exception:
                pass
            widget = child.get_backend_widget()
            try:
                # Respect per-axis stretch flags
                hexp = bool(child.stretchable(YUIDimension.YD_HORIZ) or child.weight(YUIDimension.YD_HORIZ))
                vexp = bool(child.stretchable(YUIDimension.YD_VERT) or child.weight(YUIDimension.YD_VERT))
                widget.set_hexpand(hexp)
                widget.set_vexpand(vexp)
                try:
                    widget.set_halign(Gtk.Align.FILL if hexp else Gtk.Align.CENTER)
                except Exception:
                    pass
                try:
                    widget.set_valign(Gtk.Align.FILL if vexp else Gtk.Align.CENTER)
                except Exception:
                    pass
            except Exception:
                pass

            try:
                self._backend_widget.append(widget)
            except Exception:
                try:
                    self._backend_widget.add(widget)
                except Exception:
                    pass
        self._backend_widget.set_sensitive(self._enabled)

        # If there are exactly two children and both declare positive horizontal
        # weights, attempt to enforce a proportional split according to weights.
        # Gtk.Box does not have native per-child weight factors, so we set
        # size requests on the children based on the container allocation.
        try:
            if len(children) == 2:
                w0 = int(children[0].weight(YUIDimension.YD_HORIZ) or 0)
                w1 = int(children[1].weight(YUIDimension.YD_HORIZ) or 0)
                if w0 > 0 and w1 > 0:
                    left = children[0].get_backend_widget()
                    right = children[1].get_backend_widget()
                    total_weight = max(1, w0 + w1)

                    def _apply_weights(*args):
                        try:
                            alloc = self._backend_widget.get_width()
                            if not alloc or alloc <= 0:
                                return True
                            # subtract spacing and margins conservatively
                            spacing = getattr(self._backend_widget, 'get_spacing', lambda: 5)()
                            avail = max(0, alloc - spacing)
                            left_px = int(avail * w0 / total_weight)
                            right_px = max(0, avail - left_px)
                            try:
                                left.set_size_request(left_px, -1)
                            except Exception:
                                pass
                            try:
                                right.set_size_request(right_px, -1)
                            except Exception:
                                pass
                        except Exception:
                            self._logger.exception("_apply_weights: failed", exc_info=True)
                        # remove idle after first successful sizing; keep size-allocate
                        return False

                    try:
                        GLib.idle_add(_apply_weights)
                    except Exception:
                        try:
                            # fallback: call once
                            _apply_weights()
                        except Exception:
                            pass
                    # keep children proportional on subsequent resizes if possible
                    def _on_resize_update(*_args):
                        try:
                            _apply_weights()
                        except Exception:
                            self._logger.exception("_on_resize_update: failed", exc_info=True)

                    connected = False
                    for signal_name in ("size-allocate", "notify::width", "notify::width-request"):
                        try:
                            self._backend_widget.connect(signal_name, _on_resize_update)
                            connected = True
                            self._logger.debug("Connected HBox resize hook using signal '%s'", signal_name)
                            break
                        except Exception:
                            continue
                    if not connected:
                        self._logger.debug("No supported resize signal found for HBox; dynamic weight refresh disabled")
        except Exception:
            pass
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        """Enable/disable the HBox and propagate to children."""
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    self._logger.exception("_set_backend_enabled: failed to set_sensitive", exc_info=True)
        except Exception:
            self._logger.exception("_set_backend_enabled: failed", exc_info=True)   
        try:
            for c in list(getattr(self, "_children", []) or []):
                try:
                    c.setEnabled(enabled)
                except Exception:
                    pass
        except Exception:
            pass

