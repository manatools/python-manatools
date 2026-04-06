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
from gi.repository import Gtk, GdkPixbuf, Gdk, GObject
import logging
import os
from ...yui_common import *
from .commongtk import _resolve_icon, _resolve_gicon


class YImageGtk(YWidget):
    """GTK4 image widget backed by Gtk.Picture for native scaling and SVG support.

    Gtk.Picture natively implements height-for-width geometry, preserves aspect
    ratios through ContentFit.CONTAIN, and renders SVG files at display resolution
    via librsvg when loaded with Gdk.Texture — no manual pixbuf rescaling needed.
    """

    def __init__(self, parent=None, imageFileName="", fallBackName=None):
        super().__init__(parent)
        self._imageFileName = imageFileName
        # fallBackName is reserved for text-mode backends; ignored here.
        self._fallback_name = fallBackName
        self._auto_scale = False
        self._zero_size = {YUIDimension.YD_HORIZ: False, YUIDimension.YD_VERT: False}
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        self._logger.debug("%s.__init__ file=%s", self.__class__.__name__, imageFileName)

    def widgetClass(self):
        return "YImage"

    def imageFileName(self):
        return self._imageFileName

    def setImage(self, imageFileName):
        try:
            self._imageFileName = imageFileName
            if getattr(self, '_backend_widget', None) is None:
                return
            self._load_paintable(imageFileName)
        except Exception:
            self._logger.exception("setImage failed")

    def _load_paintable(self, imageFileName):
        """Load imageFileName into the Gtk.Picture backend widget.

        Attempts in order:
        1. Gdk.Texture.new_from_filename  (GTK >= 4.6, file path only)
        2. Gdk.Texture.new_from_file      (GTK >= 4.0, via Gio.File, file path only)
        3. GdkPixbuf → Gdk.Texture        (raster fallback, file path only)
        4. Gtk.IconTheme paintable        (bare icon name resolution)

        File-based attempts (1–3) are only tried when *imageFileName* looks like
        a real filesystem path, i.e. it is absolute or contains a path separator.
        Bare names such as ``'manafirewall'`` are icon names, NOT relative file
        paths — treating them as relative paths is wrong because a same-named
        executable may exist in the current working directory, which would cause
        ``GdkPixbuf.new_from_file`` to receive a binary script as input.
        """
        # A name is treated as a file path only when it is absolute or contains
        # a directory separator.  Bare names go straight to icon theme lookup.
        is_file_path = bool(imageFileName) and (
            os.path.isabs(imageFileName) or os.sep in imageFileName
        )

        if is_file_path and os.path.exists(imageFileName):
            # Attempt 1: new_from_filename — SVG rendered at display resolution
            try:
                texture = Gdk.Texture.new_from_filename(imageFileName)
                self._backend_widget.set_paintable(texture)
                return
            except AttributeError:
                self._logger.debug(
                    "_load_paintable: Gdk.Texture.new_from_filename not available (GTK < 4.6)"
                )
            except Exception:
                self._logger.debug(
                    "_load_paintable: Gdk.Texture.new_from_filename failed for %s", imageFileName
                )

            # Attempt 2: Gio.File variant (GTK >= 4.0)
            try:
                import gi.repository.Gio as Gio
                gfile = Gio.File.new_for_path(imageFileName)
                texture = Gdk.Texture.new_from_file(gfile)
                self._backend_widget.set_paintable(texture)
                return
            except Exception:
                self._logger.debug(
                    "_load_paintable: Gdk.Texture.new_from_file failed for %s", imageFileName
                )

            # Attempt 3: GdkPixbuf raster
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(imageFileName)
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                self._backend_widget.set_paintable(texture)
                return
            except Exception:
                self._logger.exception(
                    "_load_paintable: all Gdk.Texture methods failed for %s", imageFileName
                )
            return

        # Attempt 4: resolve as a theme icon name.
        # Gtk.IconTheme.lookup_icon() returns a Gtk.IconPaintable which
        # implements Gdk.Paintable — it can be passed to set_paintable() directly
        # without needing widget realization (unlike Gtk.Image.get_paintable()).
        if imageFileName:
            try:
                base_name = (
                    os.path.splitext(imageFileName)[0]
                    if "." in imageFileName
                    else imageFileName
                )
                display = Gdk.Display.get_default()
                if display:
                    theme = Gtk.IconTheme.get_for_display(display)
                    icon_paintable = theme.lookup_icon(
                        base_name,
                        fallbacks=None,
                        size=48,
                        scale=1,
                        direction=Gtk.TextDirection.LTR,
                        flags=Gtk.IconLookupFlags.FORCE_REGULAR,
                    )
                    if icon_paintable is not None:
                        self._backend_widget.set_paintable(icon_paintable)
                        return
            except Exception:
                self._logger.debug(
                    "_load_paintable: theme icon lookup failed for %s", imageFileName
                )

        self._logger.warning("_load_paintable: could not load image: %s", imageFileName)

    def autoScale(self):
        return bool(self._auto_scale)

    def setAutoScale(self, on=True):
        try:
            self._auto_scale = bool(on)
            self._apply_size_policy()
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

    def _create_backend_widget(self):
        try:
            self._backend_widget = Gtk.Picture()
            # Allow the picture to shrink below its natural pixel size so
            # height-for-width / CONTAIN scaling works correctly.
            self._backend_widget.set_can_shrink(True)
            if self._imageFileName:
                self._load_paintable(self._imageFileName)
            self._apply_size_policy()
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            self._logger.exception("_create_backend_widget failed")

    def _apply_size_policy(self):
        """Propagate stretch/auto_scale flags to the Gtk.Picture widget.

        Key GTK4 rules:
        - hexpand/vexpand: request extra space from the parent layout.
        - halign/valign FILL: the widget fills its entire allocated rectangle
          (required so that get_width() returns the full container width).
        - ContentFit.CONTAIN: scale image to fit while preserving aspect ratio
          (GTK >= 4.8).  For older GTK, set_keep_aspect_ratio(True) is equivalent.
        """
        try:
            if getattr(self, '_backend_widget', None) is None:
                return

            stretch_h = self.stretchable(YUIDimension.YD_HORIZ)
            stretch_v = self.stretchable(YUIDimension.YD_VERT)

            self._backend_widget.set_hexpand(stretch_h)
            self._backend_widget.set_vexpand(stretch_v)
            self._backend_widget.set_halign(
                Gtk.Align.FILL if stretch_h else Gtk.Align.CENTER
            )
            self._backend_widget.set_valign(
                Gtk.Align.FILL if stretch_v else Gtk.Align.CENTER
            )

            # Aspect-ratio-preserving content fit.
            should_contain = self._auto_scale or stretch_h or stretch_v
            try:
                fit = Gtk.ContentFit.CONTAIN if should_contain else Gtk.ContentFit.SCALE_DOWN
                self._backend_widget.set_content_fit(fit)
            except AttributeError:
                # GTK < 4.8: keep_aspect_ratio is the equivalent flag.
                self._backend_widget.set_keep_aspect_ratio(should_contain)
        except Exception:
            self._logger.exception("_apply_size_policy failed")

    def setStretchable(self, dim, new_stretch):
        try:
            super().setStretchable(dim, new_stretch)
        except Exception:
            pass
        try:
            self._apply_size_policy()
        except Exception:
            pass
