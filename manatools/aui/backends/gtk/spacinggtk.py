# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
GTK backend: YSpacing implementation using an empty Gtk.Box with size requests.

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
'''
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk
import logging
from ...yui_common import *


class YSpacingGtk(YWidget):
    """Spacing/Stretch widget for GTK.

    - `dim`: primary dimension (horizontal or vertical) where spacing applies
    - `stretchable`: whether the spacing expands in its primary dimension
    - `size`: spacing size in pixels (device units). Pixels are used for clarity
      and uniformity across backends; GTK honors `set_size_request` in pixels.
    """
    def __init__(self, parent=None, dim: YUIDimension = YUIDimension.YD_HORIZ, stretchable: bool = False, size: float = 0.0):
        super().__init__(parent)
        self._dim = dim
        self._stretchable = bool(stretchable)
        try:
            self._size_px = max(0, int(round(float(size))))
        except Exception:
            self._size_px = 0
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        try:
            self._logger.debug("%s.__init__(dim=%s, stretchable=%s, size_px=%d)", self.__class__.__name__, self._dim, self._stretchable, self._size_px)
        except Exception:
            pass

    def widgetClass(self):
        return "YSpacing"

    def dimension(self):
        return self._dim

    def size(self):
        return self._size_px

    def sizeDim(self, dim: YUIDimension):
        return self._size_px if dim == self._dim else 0

    def _create_backend_widget(self):
        try:
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            # size request in the primary dimension
            if self._dim == YUIDimension.YD_HORIZ:
                try:
                    if self._stretchable:
                        box.set_hexpand(True)
                        box.set_halign(Gtk.Align.FILL)
                        box.set_size_request(self._size_px, -1)
                    else:
                        box.set_hexpand(False)
                        box.set_halign(Gtk.Align.CENTER)
                        box.set_size_request(self._size_px, -1)
                    box.set_vexpand(False)
                    box.set_valign(Gtk.Align.CENTER)
                except Exception:
                    pass
            else:
                try:
                    if self._stretchable:
                        box.set_vexpand(True)
                        box.set_valign(Gtk.Align.FILL)
                        box.set_size_request(-1, self._size_px)
                    else:
                        box.set_vexpand(False)
                        box.set_valign(Gtk.Align.CENTER)
                        box.set_size_request(-1, self._size_px)
                    box.set_hexpand(False)
                    box.set_halign(Gtk.Align.CENTER)
                except Exception:
                    pass
            self._backend_widget = box
            self._backend_widget.set_sensitive(self._enabled)
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            try:
                self._logger.exception("Failed to create YSpacingGtk backend")
            except Exception:
                pass
            self._backend_widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

    def _set_backend_enabled(self, enabled):
        try:
            if self._backend_widget is not None:
                self._backend_widget.set_sensitive(bool(enabled))
        except Exception:
            pass
