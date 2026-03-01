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
        """Create the GTK4 HBox backend and apply weight-based horizontal sizing.

        Gtk.Box does not natively support per-child stretch factors.  This
        method installs a resize callback (``notify::width``) that translates
        YWidget horizontal weights into ``set_size_request(px, -1)`` calls.

        Rules:
        * Children with ``weight(YD_HORIZ) > 0`` share available horizontal
          space proportionally to their weights.
        * Children with weight=0 get their natural width and are excluded from
          the weighted pool.
        * All children with ``stretchable(YD_HORIZ)`` or positive weight get
          ``set_hexpand(True)`` so GTK still allows them to grow.
        * Works for any number of children.
        """
        self._backend_widget = _YHBoxMeasureBox(self)

        # Snapshot children list once; weight application reads from this snapshot.
        children = list(self._children)

        for child in children:
            widget = child.get_backend_widget()
            try:
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
                self._logger.debug(
                    "_create_backend_widget child=%s hexp=%s vexp=%s weight_h=%s weight_v=%s",
                    child.debugLabel(), hexp, vexp,
                    child.weight(YUIDimension.YD_HORIZ), child.weight(YUIDimension.YD_VERT),
                )
            except Exception:
                self._logger.exception("HBox: failed to configure expand/align for child")

            try:
                self._backend_widget.append(widget)
            except Exception:
                try:
                    self._backend_widget.add(widget)
                except Exception:
                    self._logger.exception("HBox: failed to append child widget")

        self._backend_widget.set_sensitive(self._enabled)
        self._logger.debug("_create_backend_widget: <%s> children=%d", self.debugLabel(), len(children))

        # --- Weight-based horizontal size distribution ---
        # Children with weight(YD_HORIZ) > 0 share available width
        # proportionally; weight=0 children keep their natural width.
        try:
            child_hweights = []
            for c in children:
                try:
                    w = int(c.weight(YUIDimension.YD_HORIZ) or 0)
                except Exception:
                    w = 0
                child_hweights.append(w)

            total_weight = sum(child_hweights)
            has_weighted = total_weight > 0

            if has_weighted:
                backend_widgets = []
                for c in children:
                    try:
                        backend_widgets.append(c.get_backend_widget())
                    except Exception:
                        backend_widgets.append(None)

                self._logger.debug(
                    "HBox weight distribution enabled: weights=%s total=%d",
                    child_hweights, total_weight,
                )

                def _apply_weights(*_args):
                    """Compute and apply size_request per child from current allocation.

                    Called on the first idle tick and on ``notify::width`` for
                    subsequent resizes.
                    """
                    try:
                        alloc = self._backend_widget.get_width()
                        if not alloc or alloc <= 0:
                            self._logger.debug("HBox _apply_weights: no allocation yet, skipping")
                            return True  # retry via idle

                        spacing = 5
                        try:
                            spacing = int(self._backend_widget.get_spacing())
                        except Exception:
                            pass

                        n_visible = sum(1 for bw in backend_widgets if bw is not None)
                        gap_total = max(0, n_visible - 1) * spacing

                        # Reserve natural width of unweighted children.
                        fixed_total = 0
                        for idx, bw in enumerate(backend_widgets):
                            if bw is None or child_hweights[idx] > 0:
                                continue
                            try:
                                _, nat, _, _ = bw.measure(Gtk.Orientation.HORIZONTAL, -1)
                                fixed_total += max(0, int(nat))
                            except Exception:
                                pass

                        avail = max(0, alloc - gap_total - fixed_total)
                        self._logger.debug(
                            "HBox _apply_weights: alloc=%d gap=%d fixed=%d avail=%d weights=%s",
                            alloc, gap_total, fixed_total, avail, child_hweights,
                        )

                        allocated_px = []
                        remainder = avail
                        for idx, w in enumerate(child_hweights):
                            if w <= 0:
                                allocated_px.append(None)
                            else:
                                px = int(avail * w / total_weight)
                                allocated_px.append(px)
                                remainder -= px

                        # Give remainder to the last weighted child.
                        if remainder > 0:
                            for idx in range(len(allocated_px) - 1, -1, -1):
                                if allocated_px[idx] is not None:
                                    allocated_px[idx] += remainder
                                    break

                        for bw, px in zip(backend_widgets, allocated_px):
                            if bw is None or px is None:
                                continue
                            try:
                                bw.set_size_request(max(1, px), -1)
                            except Exception:
                                pass

                        self._logger.debug("HBox _apply_weights: applied=%s", allocated_px)
                    except Exception:
                        self._logger.exception("HBox _apply_weights: unexpected failure")
                    return False  # remove from idle queue after first success

                try:
                    GLib.idle_add(_apply_weights)
                except Exception:
                    self._logger.exception("HBox: GLib.idle_add failed; applying weights immediately")
                    try:
                        _apply_weights()
                    except Exception:
                        pass

                def _on_resize(*_args):
                    """Re-apply weights after the container is resized."""
                    try:
                        _apply_weights()
                    except Exception:
                        self._logger.exception("HBox _on_resize: weight re-application failed")

                connected = False
                for sig in ("notify::width", "size-allocate"):
                    try:
                        self._backend_widget.connect(sig, _on_resize)
                        connected = True
                        self._logger.debug("HBox connected resize signal '%s'", sig)
                        break
                    except Exception:
                        continue
                if not connected:
                    self._logger.warning(
                        "HBox: no resize signal available; weight proportions will not "
                        "update on window resize"
                    )
        except Exception:
            self._logger.exception("HBox weight distribution setup failed")

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

