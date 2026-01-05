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


class YHBoxGtk(YWidget):
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

    def _create_backend_widget(self):
        self._backend_widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

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
                            alloc = self._backend_widget.get_allocated_width()
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
                            pass
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
                    try:
                        def _on_size_allocate(widget, allocation):
                            try:
                                _apply_weights()
                            except Exception:
                                pass
                        self._backend_widget.connect('size-allocate', _on_size_allocate)
                    except Exception:
                        pass
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
                    pass
        except Exception:
            pass
        try:
            for c in list(getattr(self, "_children", []) or []):
                try:
                    c.setEnabled(enabled)
                except Exception:
                    pass
        except Exception:
            pass

