# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
"""
Python manatools.aui.backends.gtk contains GTK backend for YImage

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, GdkPixbuf, GObject
import logging
import os
from ...yui_common import *
from .commongtk import _resolve_icon, _resolve_gicon


class YImageGtk(YWidget):
    def __init__(self, parent=None, imageFileName=""):
        super().__init__(parent)
        self._imageFileName = imageFileName
        self._auto_scale = False
        self._zero_size = {YUIDimension.YD_HORIZ: False, YUIDimension.YD_VERT: False}
        self._pixbuf = None
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        self._logger.debug("%s.__init__ file=%s", self.__class__.__name__, imageFileName)

    def widgetClass(self):
        return "YImage"

    def imageFileName(self):
        return self._imageFileName

    def setImage(self, imageFileName):
        try:
            self._imageFileName = imageFileName
            if getattr(self, '_backend_widget', None) is not None:
                # Try resolving via common GTK helper (may be theme icon or file)
                try:
                    resolved = _resolve_icon(imageFileName, size=48)
                    if resolved is not None:
                        # If helper returned a Gtk.Image, attempt to set it on backend
                        try:
                            paintable = resolved.get_paintable() if hasattr(resolved, 'get_paintable') else None
                            if paintable:
                                self._backend_widget.set_from_paintable(paintable)
                                return
                        except Exception:
                            pass
                        try:
                            pix = resolved.get_pixbuf() if hasattr(resolved, 'get_pixbuf') else None
                            if pix:
                                self._pixbuf = pix
                                self._apply_pixbuf()
                                return
                        except Exception:
                            pass
                except Exception:
                    pass

                # Fallback: try to load from file directly
                if os.path.exists(imageFileName):
                    try:
                        self._pixbuf = GdkPixbuf.Pixbuf.new_from_file(imageFileName)
                        self._apply_pixbuf()
                    except Exception:
                        self._logger.exception("failed to load pixbuf")
                else:
                    self._logger.error("setImage: file not found: %s", imageFileName)
        except Exception:
            self._logger.exception("setImage failed")

    def autoScale(self):
        return bool(self._auto_scale)

    def setAutoScale(self, on=True):
        try:
            self._auto_scale = bool(on)
            self._apply_size_policy()
            self._apply_pixbuf()
        except Exception:
            self._logger.exception("setAutoScale failed")

    def hasZeroSize(self, dim):
        return bool(self._zero_size.get(dim, False))

    def setZeroSize(self, dim, zeroSize=True):
        self._zero_size[dim] = bool(zeroSize)
        try:
            self._apply_size_policy()
        except Exception:
            pass

    def _on_size_allocate(self, widget, allocation):
        try:
            if self._auto_scale and self._pixbuf is not None:
                self._apply_pixbuf()
        except Exception:
            self._logger.exception("_on_size_allocate failed")

    def _create_backend_widget(self):
        try:
            self._backend_widget = Gtk.Image()
            if self._imageFileName and os.path.exists(self._imageFileName):
                try:
                    self._pixbuf = GdkPixbuf.Pixbuf.new_from_file(self._imageFileName)
                except Exception:
                    self._logger.exception("failed to load pixbuf")
            if getattr(self, '_pixbuf', None) is not None:
                self._apply_pixbuf()
            # hook allocation to rescale if autoscale is enabled
            try:
                self._backend_widget.connect('size-allocate', self._on_size_allocate)
            except Exception:
                pass
            self._apply_size_policy()
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            self._logger.exception("_create_backend_widget failed")

    def _apply_size_policy(self):
        try:
            if getattr(self, '_backend_widget', None) is None:
                return
            try:
                if hasattr(self._backend_widget, 'set_hexpand'):
                    self._backend_widget.set_hexpand(self._auto_scale or self.stretchable(YUIDimension.YD_HORIZ))
            except Exception:
                pass
            try:
                if hasattr(self._backend_widget, 'set_vexpand'):
                    self._backend_widget.set_vexpand(self._auto_scale or self.stretchable(YUIDimension.YD_VERT))
            except Exception:
                pass
        except Exception:
            self._logger.exception("_apply_size_policy failed")

    def _apply_pixbuf(self):
        try:
            if getattr(self, '_backend_widget', None) is None:
                return
            if not self._pixbuf:
                self._backend_widget.clear()
                return
            if self._auto_scale and hasattr(self._backend_widget, 'get_allocated_width'):
                try:
                    w = self._backend_widget.get_allocated_width()
                    h = self._backend_widget.get_allocated_height()
                    if w > 1 and h > 1:
                        scaled = self._pixbuf.scale_simple(w, h, GdkPixbuf.InterpType.BILINEAR)
                        self._backend_widget.set_from_pixbuf(scaled)
                        return
                except Exception:
                    pass
            # fallback: set original pixbuf
            self._backend_widget.set_from_pixbuf(self._pixbuf)
        except Exception:
            self._logger.exception("_apply_pixbuf failed")

    def setStretchable(self, dim, new_stretch):
        try:
            super().setStretchable(dim, new_stretch)
        except Exception:
            pass
        try:
            self._apply_size_policy()
        except Exception:
            pass
