"""Web backend Image implementation."""
import os
import re
import base64
import mimetypes
import logging
from ...yui_common import YWidget
from .commonweb import widget_attrs, escape_html

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
        attrs = widget_attrs(self.id(), "YImage", True, self._visible)
        src = self._resolve_src()

        if src:
            extra = ' class="mana-yimage-img"'
            if self._auto_scale:
                extra += ' style="max-width:100%;height:auto"'
            img = f'<img{extra} src="{escape_html(src)}" alt="">'
        else:
            img = ""

        return f'<div {attrs}>{img}</div>'
