"""
Web backend HtmlView implementation.

The sanitized document is never inlined into the dialog page.  The backend's
own server serves it from ``/htmlview/<token>`` into an ``<iframe sandbox>``
that runs no script, has an opaque origin and carries its own restrictive
CSP (see ``ManaToolsRequestHandler._serve_htmlview``).

Links point at ``/htmlview/<token>/link/<n>``: following one asks the server,
which answers 204 No Content (so the frame never navigates) and reports
activation of link *n*.  The token is random and rotates on every content
change, so a stale frame or another page cannot fire activations.

Author: Matteo Pasotti <xquiet@coriolite.com>

License: LGPLv2+
"""

import secrets
import threading
import weakref
from typing import Optional

from ...yui_common import YHtmlViewBase
from .commonweb import widget_attrs


class YHtmlViewWeb(YHtmlViewBase):
    """Read-only HTML view rendered in a sandboxed iframe."""

    # token -> widget, for the server routes.  Weak so a destroyed dialog's
    # widgets do not stay reachable through a leaked URL.
    _by_token = weakref.WeakValueDictionary()
    _lock = threading.RLock()

    def __init__(self, parent=None, html: str = ""):
        # Attributes first: addChild() on the parent may render us immediately.
        self._token = None
        super().__init__(parent, html)

    def setHelpText(self, help_text: str):
        super().setHelpText(help_text)
        self._notify_update()

    def setVisible(self, visible: bool = True):
        self._visible = bool(visible)
        self._notify_update()

    def _set_backend_enabled(self, enabled: bool):
        self._notify_update()

    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)

    # -- token management ---------------------------------------------------

    def _current_token(self) -> str:
        with YHtmlViewWeb._lock:
            if self._token is None:
                self._token = secrets.token_urlsafe(24)
                YHtmlViewWeb._by_token[self._token] = self
            return self._token

    def _content_changed(self):
        # Drop the cached document and its token together: the next render
        # gets a fresh URL and links of the old content stop working.
        with YHtmlViewWeb._lock:
            self._rendered = None
            if self._token is not None:
                YHtmlViewWeb._by_token.pop(self._token, None)
                self._token = None
        self._notify_update()

    def _link_href(self, index: int) -> str:
        return f"/htmlview/{self._current_token()}/link/{index}"

    @classmethod
    def _lookup(cls, token: str) -> Optional["YHtmlViewWeb"]:
        with cls._lock:
            return cls._by_token.get(token)

    # -- server entry points (called from request threads) ------------------

    def _serve_document(self, token: str) -> Optional[tuple]:
        """Return (document, allow_remote) for *token*, or None if stale."""
        with YHtmlViewWeb._lock:
            if token != self._token:
                return None
            return self._sanitized().document, self._allow_remote

    def _serve_link(self, token: str, index: int) -> bool:
        """Activate link *index* if *token* is still the current one."""
        with YHtmlViewWeb._lock:
            if token != self._token:
                return False
        return self._activate_link(index)

    # -- rendering ----------------------------------------------------------

    def render(self) -> str:
        token = self._current_token()
        extra_classes = "" if self._enabled else "mana-disabled"
        attrs = widget_attrs(self.id(), "YHtmlView", True, self._visible,
                             extra_classes,
                             extra_attrs={"title": self.helpText() or None})
        return (f'<div {attrs}>'
                f'<iframe class="mana-htmlview-frame" src="/htmlview/{token}"'
                f' sandbox="" referrerpolicy="no-referrer" title="HTML content">'
                f'</iframe></div>')
