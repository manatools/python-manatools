"""Web backend Image implementation."""
import os
import re
import base64
import mimetypes
import logging
from ...yui_common import YWidget, YUIDimension
from .commonweb import widget_attrs, escape_html, schedule_update_if_open

logger = logging.getLogger("manatools.aui.web.YImageWeb")

# Matches bare XDG icon names (no path separators, no extension required).
_ICON_NAME_RE = re.compile(r'^[a-zA-Z0-9_\-]+$')


class YImageWeb(YWidget):
    """Image display widget."""

    def __init__(self, parent=None, imageFileName: str = "", fallBackName=None):
        super().__init__(parent)
        self._image_file = imageFileName
        self._fallback_name = fallBackName
        self._auto_scale = False
        self._zero_size = {YUIDimension.YD_HORIZ: False, YUIDimension.YD_VERT: False}

    def widgetClass(self):
        return "YImage"

    def imageFileName(self) -> str:
        return self._image_file

    def setImage(self, imageFileName: str):
        self._image_file = imageFileName
        self._notify_update()

    def autoScale(self) -> bool:
        return self._auto_scale

    def setAutoScale(self, on: bool = True):
        self._auto_scale = bool(on)
        self._notify_update()

    def hasZeroSize(self, dim) -> bool:
        # getattr: a parent may render us before __init__ has finished.
        return bool(getattr(self, "_zero_size", {}).get(dim, False))

    def setZeroSize(self, dim, zeroSize: bool = True):
        """Let the image shrink to nothing in *dim* instead of imposing its
        natural size on the layout."""
        if not hasattr(self, "_zero_size"):
            self._zero_size = {}
        self._zero_size[dim] = bool(zeroSize)
        self._notify_update()

    def setStretchable(self, dim, new_stretch: bool):
        super().setStretchable(dim, new_stretch)
        # Stretch is applied by the parent box's layout: re-render the parent.
        schedule_update_if_open(self._parent if self._parent is not None else self)

    def _set_backend_enabled(self, enabled: bool):
        self._notify_update()

    def setVisible(self, visible: bool = True):
        self._visible = bool(visible)
        self._notify_update()

    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)

    def _resolve_src(self) -> str:
        """Return a browser-usable src value for the <img> element.

        Resolution order:
        1. Already a URL (http/https/data) — used as-is.
        2. Filesystem path (absolute or contains os.sep) — read and returned as
           a base64 data URI so the browser never needs to access the filesystem.
        3. Bare icon name matching [a-zA-Z0-9_-] — routed through the existing
           /icon/<name> HTTP endpoint which performs XDG icon theme lookup.
        4. fallBackName is tried for cases 2 and 3 when the primary name fails.
        """
        src = self._try_resolve(self._image_file)
        if not src and self._fallback_name:
            src = self._try_resolve(self._fallback_name)
        return src

    def _try_resolve(self, filename: str) -> str:
        if not filename:
            return ""

        # Already a URL or data URI — use directly.
        if filename.startswith(('http://', 'https://', 'data:')):
            return filename

        # Filesystem path → inline as base64 data URI.
        is_file_path = os.path.isabs(filename) or os.sep in filename
        if is_file_path:
            if os.path.isfile(filename):
                try:
                    mime, _ = mimetypes.guess_type(filename)
                    mime = mime or "image/png"
                    with open(filename, "rb") as fh:
                        encoded = base64.b64encode(fh.read()).decode("ascii")
                    return f"data:{mime};base64,{encoded}"
                except Exception:
                    logger.warning("YImageWeb: cannot read image file: %s", filename)
            return ""

        # Bare icon name (strip extension if present, e.g. "manafirewall.png" → "manafirewall").
        name = os.path.splitext(filename)[0] if "." in filename else filename
        if _ICON_NAME_RE.match(name):
            return f"/icon/{name}"

        return ""

    def render(self) -> str:
        # Wrap in a <div> so the widget has a stable container node that can be
        # replaced by _flush_update.  enabled=True: <div> must not carry disabled.
        zero_w = self.hasZeroSize(YUIDimension.YD_HORIZ)
        zero_h = self.hasZeroSize(YUIDimension.YD_VERT)
        box_style = "; ".join(
            ([] if not zero_w else ["min-width: 0", "width: 0", "flex-basis: 0"])
            + ([] if not zero_h else ["min-height: 0", "height: 0"])
            + (["overflow: hidden"] if (zero_w or zero_h) else []))
        attrs = widget_attrs(self.id(), "YImage", True, self._visible,
                             extra_attrs={"style": box_style or None})
        src = self._resolve_src()

        if src:
            extra = ' class="mana-yimage-img"'
            img_style = []
            if self._auto_scale or zero_w:
                img_style.append("max-width:100%")
            if zero_h:
                img_style.append("max-height:100%")
            if self._auto_scale:
                img_style.append("height:auto")
            if img_style:
                extra += f' style="{";".join(img_style)}"'
            img = f'<img{extra} src="{escape_html(src)}" alt="">'
        else:
            img = ""

        return f'<div {attrs}>{img}</div>'
