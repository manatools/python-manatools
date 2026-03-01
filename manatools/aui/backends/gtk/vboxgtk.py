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


class _YVBoxMeasureBox(Gtk.Box):
    """Gtk.Box subclass delegating size requests to YVBoxGtk."""

    def __init__(self, owner):
        """Initialize the measuring box.

        Args:
            owner: Owning YVBoxGtk instance.
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=5)
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
            self._owner._logger.exception("VBox backend do_measure delegation failed", exc_info=True)
            return (0, 0, -1, -1)


class YVBoxGtk(YWidget):
    """Vertical GTK4 container with weight-aware geometry management."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
    
    def widgetClass(self):
        return "YVBox"
    
    # Returns the stretchability of the layout box:
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
            self._logger.exception("Failed to read VBox spacing for measure", exc_info=True)
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
                self._logger.exception("VBox measure failed for child %s", getattr(child, "debugLabel", lambda: "<unknown>")(), exc_info=True)
                cmin, cnat = 0, 0

            if orientation == Gtk.Orientation.VERTICAL:
                minimum_size += int(cmin)
                natural_size += int(cnat)
            else:
                maxima_minimum = max(maxima_minimum, int(cmin))
                maxima_natural = max(maxima_natural, int(cnat))

        if orientation == Gtk.Orientation.VERTICAL:
            gap_total = max(0, len(children) - 1) * spacing
            minimum_size += gap_total
            natural_size += gap_total
        else:
            minimum_size = maxima_minimum
            natural_size = maxima_natural

        self._logger.debug(
            "VBox do_measure orientation=%s for_size=%s -> min=%s nat=%s",
            orientation,
            for_size,
            minimum_size,
            natural_size,
        )
        return (minimum_size, natural_size, -1, -1)

    def _create_backend_widget(self):
        """Create the GTK4 VBox backend and apply weight-based vertical sizing.

        Gtk.Box does not natively support per-child stretch factors, so this
        method installs a resize callback (``notify::height``) that translates
        YWidget weights into ``set_size_request(-1, px)`` calls.

        Rules:
        * Children with ``weight(YD_VERT) > 0`` share available vertical space
          proportionally to their weights.
        * Children with weight=0 get their natural height and are excluded from
          the weighted allocation pool.
        * All children with ``stretchable(YD_VERT)`` or positive weight receive
          ``set_vexpand(True)`` so GTK still allows them to grow.
        * Works for any number of children.
        """
        self._backend_widget = _YVBoxMeasureBox(self)

        # Snapshot children list once; weight application reads from this snapshot.
        children = list(self._children)

        for child in children:
            widget = child.get_backend_widget()
            try:
                vert_stretch = bool(child.stretchable(YUIDimension.YD_VERT)) or bool(child.weight(YUIDimension.YD_VERT))
                horiz_stretch = bool(child.stretchable(YUIDimension.YD_HORIZ)) or bool(child.weight(YUIDimension.YD_HORIZ))
                widget.set_vexpand(bool(vert_stretch))
                widget.set_hexpand(bool(horiz_stretch))
                try:
                    widget.set_valign(Gtk.Align.FILL if vert_stretch else Gtk.Align.START)
                except Exception:
                    pass
                try:
                    widget.set_halign(Gtk.Align.FILL if horiz_stretch else Gtk.Align.START)
                except Exception:
                    pass
                self._logger.debug(
                    "_create_backend_widget child=%s vstretch=%s hstretch=%s weight_v=%s weight_h=%s",
                    child.debugLabel(), vert_stretch, horiz_stretch,
                    child.weight(YUIDimension.YD_VERT), child.weight(YUIDimension.YD_HORIZ),
                )
            except Exception:
                self._logger.exception("VBox: failed to configure expand/align for child")

            try:
                self._backend_widget.append(widget)
            except Exception:
                try:
                    self._backend_widget.add(widget)
                except Exception:
                    self._logger.exception("VBox: failed to append child widget")

        self._backend_widget.set_sensitive(self._enabled)
        self._logger.debug("_create_backend_widget: <%s> children=%d", self.debugLabel(), len(children))

        # --- Weight-based vertical size distribution ---
        # Collect per-child vertical weights.  Any child whose weight > 0
        # participates in proportional allocation; weight=0 children get their
        # natural height and are subtracted from the available pool first.
        try:
            child_vweights = []
            for c in children:
                try:
                    w = int(c.weight(YUIDimension.YD_VERT) or 0)
                except Exception:
                    w = 0
                child_vweights.append(w)

            total_weight = sum(child_vweights)
            has_weighted = total_weight > 0

            if has_weighted:
                # Capture backend widgets for the closure below.
                backend_widgets = []
                for c in children:
                    try:
                        backend_widgets.append(c.get_backend_widget())
                    except Exception:
                        backend_widgets.append(None)

                self._logger.debug(
                    "VBox weight distribution enabled: weights=%s total=%d",
                    child_vweights, total_weight,
                )

                def _apply_vweights(*_args):
                    """Compute and apply size_request per child from current allocation.

                    Called on the first idle tick and on every ``notify::height``
                    to keep proportions correct after window resize.  Returns
                    False from idle so it fires only once (the notify signal
                    takes over for subsequent resizes).
                    """
                    try:
                        alloc = self._backend_widget.get_height()
                        if not alloc or alloc <= 0:
                            self._logger.debug("VBox _apply_vweights: no allocation yet, skipping")
                            return True  # retry via idle

                        spacing = 5
                        try:
                            spacing = int(self._backend_widget.get_spacing())
                        except Exception:
                            pass

                        # Total gap between children
                        n_visible = sum(1 for bw in backend_widgets if bw is not None)
                        gap_total = max(0, n_visible - 1) * spacing

                        # Measure natural height of unweighted children so we can
                        # reserve their space before distributing the remainder.
                        fixed_total = 0
                        for idx, bw in enumerate(backend_widgets):
                            if bw is None or child_vweights[idx] > 0:
                                continue  # weighted; will be sized below
                            try:
                                _, nat, _, _ = bw.measure(Gtk.Orientation.VERTICAL, -1)
                                fixed_total += max(0, int(nat))
                            except Exception:
                                pass  # no natural size info; ignore

                        avail = max(0, alloc - gap_total - fixed_total)
                        self._logger.debug(
                            "VBox _apply_vweights: alloc=%d gap=%d fixed=%d avail=%d weights=%s",
                            alloc, gap_total, fixed_total, avail, child_vweights,
                        )

                        # Distribute available space proportionally.
                        allocated_px = []
                        remainder = avail
                        for idx, w in enumerate(child_vweights):
                            if w <= 0:
                                allocated_px.append(None)  # natural size; no override
                            else:
                                px = int(avail * w / total_weight)
                                allocated_px.append(px)
                                remainder -= px

                        # Give integer rounding remainder to the last weighted child.
                        if remainder > 0:
                            for idx in range(len(allocated_px) - 1, -1, -1):
                                if allocated_px[idx] is not None:
                                    allocated_px[idx] += remainder
                                    break

                        # Apply computed sizes.
                        for bw, px in zip(backend_widgets, allocated_px):
                            if bw is None or px is None:
                                continue
                            try:
                                bw.set_size_request(-1, max(1, px))
                            except Exception:
                                pass

                        self._logger.debug("VBox _apply_vweights: applied=%s", allocated_px)
                    except Exception:
                        self._logger.exception("VBox _apply_vweights: unexpected failure")
                    return False  # remove from idle queue after first success

                # Schedule first application and connect for subsequent resizes.
                try:
                    GLib.idle_add(_apply_vweights)
                except Exception:
                    self._logger.exception("VBox: GLib.idle_add failed; applying weights immediately")
                    try:
                        _apply_vweights()
                    except Exception:
                        pass

                def _on_resize(*_args):
                    """Re-apply weights after the container is resized."""
                    try:
                        _apply_vweights()
                    except Exception:
                        self._logger.exception("VBox _on_resize: weight re-application failed")

                # ``notify::height`` is the recommended signal in GTK4.
                # Fall back to ``size-allocate`` for older GTK4 micro-versions.
                connected = False
                for sig in ("notify::height", "size-allocate"):
                    try:
                        self._backend_widget.connect(sig, _on_resize)
                        connected = True
                        self._logger.debug("VBox connected resize signal '%s'", sig)
                        break
                    except Exception:
                        continue
                if not connected:
                    self._logger.warning(
                        "VBox: no resize signal available; weight proportions will not "
                        "update on window resize"
                    )
        except Exception:
            self._logger.exception("VBox weight distribution setup failed")


    def _set_backend_enabled(self, enabled):
        """Enable/disable the VBox and propagate to children."""
        try:
            if self._backend_widget is not None:
                try:
                    self._backend_widget.set_sensitive(enabled)
                except Exception:
                    self._logger.exception("_set_backend_enabled: failed to set_sensitive", exc_info=True)
        except Exception:
            self._logger.exception("_set_backend_enabled: failed", exc_info=True)
        # propagate logical enabled state to child widgets so they update their backends
        try:
            for c in list(getattr(self, "_children", []) or []):
                try:
                    c.setEnabled(enabled)
                except Exception:
                    pass
        except Exception:
            pass
