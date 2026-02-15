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
        """Create backend widget and configure weight/stretch behavior."""
        self._backend_widget = _YVBoxMeasureBox(self)
        
        # Collect children first so we can apply weight-based heuristics
        children = list(self._children)

        for child in children:
            widget = child.get_backend_widget()
            try:
                # Respect the child's stretchable/weight hints instead of forcing expansion
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
            except Exception:
                pass

            # Gtk4: use append instead of pack_start
            try:
                self._backend_widget.append(widget)
            except Exception:
                try:
                    self._backend_widget.add(widget)
                except Exception:
                    pass
        self._backend_widget.set_sensitive(self._enabled)
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

        # If there are exactly two children and both declare positive vertical
        # weights, attempt to enforce a proportional vertical split according
        # to weights. Similar to horizontal HBox, Gtk.Box does not support
        # per-child weight factors, so we set size requests on the children
        # based on the container allocation.
        try:
            if len(children) == 2:
                w0 = int(children[0].weight(YUIDimension.YD_VERT) or 0)
                w1 = int(children[1].weight(YUIDimension.YD_VERT) or 0)
                if w0 > 0 and w1 > 0:
                    top = children[0].get_backend_widget()
                    bottom = children[1].get_backend_widget()
                    total_weight = max(1, w0 + w1)

                    def _apply_vweights(*args):
                        try:
                            alloc = self._backend_widget.get_height()
                            if not alloc or alloc <= 0:
                                return True
                            spacing = getattr(self._backend_widget, 'get_spacing', lambda: 5)()
                            avail = max(0, alloc - spacing)
                            top_px = int(avail * w0 / total_weight)
                            bot_px = max(0, avail - top_px)
                            try:
                                top.set_size_request(-1, top_px)
                            except Exception:
                                pass
                            try:
                                bottom.set_size_request(-1, bot_px)
                            except Exception:
                                pass
                        except Exception:
                            self._logger.exception("_apply_vweights: failed", exc_info=True)
                        return False

                    try:
                        GLib.idle_add(_apply_vweights)
                    except Exception:
                        try:
                            _apply_vweights()
                        except Exception:
                            pass
                    def _on_resize_update(*_args):
                        try:
                            _apply_vweights()
                        except Exception:
                            self._logger.exception("_on_resize_update: failed", exc_info=True)

                    connected = False
                    for signal_name in ("size-allocate", "notify::height", "notify::height-request"):
                        try:
                            self._backend_widget.connect(signal_name, _on_resize_update)
                            connected = True
                            self._logger.debug("Connected VBox resize hook using signal '%s'", signal_name)
                            break
                        except Exception:
                            continue
                    if not connected:
                        self._logger.debug("No supported resize signal found for VBox; dynamic weight refresh disabled")
        except Exception:
            pass


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
