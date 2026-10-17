# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
GTK4 backend YHtmlView.

Engine: WebKitGTK 6.0 (gi namespace ``WebKit``) when installed, hardened:
- an ephemeral network session (nothing written to disk);
- JavaScript (including markup-defined handlers), WebGL, media, local
  storage, page cache, developer tools and file-URL access are off;
- every navigation is refused except loading our own document; link clicks
  are reported as activations, new windows never open, the context menu is
  suppressed;
- remote loads are stopped by the sanitizer and by the document's CSP.
WebKit renders in its own sandboxed web process.

Fallback (no WebKitGTK 6.0): the sanitized content flattened to Pango markup
in a selectable Gtk.Label; links stay clickable and are reported the same
way.

Content always goes through YHtmlViewBase sanitizing first.

License: LGPLv2+

@package manatools.aui.backends.gtk
'''
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Pango
import logging
from ...yui_common import *

_webkit_module = None


def _webkit():
    """Return the WebKit 6.0 gi module, or False if unavailable."""
    global _webkit_module
    if _webkit_module is None:
        try:
            gi.require_version('WebKit', '6.0')
            from gi.repository import WebKit
            _webkit_module = WebKit
        except Exception:
            _webkit_module = False
    return _webkit_module


class YHtmlViewGtk(YHtmlViewBase):
    """Read-only, hardened HTML view (WebKitGTK 6.0, Gtk.Label fallback)."""

    def __init__(self, parent=None, html: str = ""):
        # Attributes first: addChild() on the parent may build us immediately.
        self._engine = None          # "webkit" or "label"
        self._content_widget = None
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        super().__init__(parent, html)

    # -- backend construction -----------------------------------------------

    def _create_webkit_view(self, WebKit):
        try:
            session = WebKit.NetworkSession.new_ephemeral()
            view = WebKit.WebView(network_session=session)
        except Exception:
            view = WebKit.WebView()
        settings = view.get_settings()
        for prop, value in (("enable-javascript", False),
                            ("enable-javascript-markup", False),
                            ("javascript-can-open-windows-automatically", False),
                            ("javascript-can-access-clipboard", False),
                            ("enable-webgl", False),
                            ("enable-webaudio", False),
                            ("enable-media", False),
                            ("enable-html5-database", False),
                            ("enable-html5-local-storage", False),
                            ("enable-page-cache", False),
                            ("enable-developer-extras", False),
                            ("enable-hyperlink-auditing", False),
                            ("enable-dns-prefetching", False),
                            ("allow-file-access-from-file-urls", False),
                            ("allow-universal-access-from-file-urls", False),
                            ("allow-modal-dialogs", False),
                            ("auto-load-images", True)):
            try:
                settings.set_property(prop, value)
            except Exception:
                # Property absent in this WebKit version: nothing to disable.
                self._logger.debug("WebKit setting %s unavailable", prop)

        view.connect("decide-policy", self._on_decide_policy, WebKit)
        view.connect("context-menu", lambda *_args: True)
        return view

    def _on_decide_policy(self, _view, decision, decision_type, WebKit):
        PolicyType = WebKit.PolicyDecisionType
        if decision_type not in (PolicyType.NAVIGATION_ACTION, PolicyType.NEW_WINDOW_ACTION):
            return False
        try:
            action = decision.get_navigation_action()
            uri = action.get_request().get_uri() or ""
            link_clicked = action.get_navigation_type() == WebKit.NavigationType.LINK_CLICKED
        except Exception:
            decision.ignore()
            return True
        if link_clicked or self._link_index(uri) is not None:
            decision.ignore()
            self._on_link(uri)
            return True
        # Only our own load_html() document may load in the main frame.
        if decision_type == PolicyType.NAVIGATION_ACTION and uri in ("", "about:blank"):
            decision.use()
        else:
            decision.ignore()
        return True

    def _create_label_view(self):
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        try:
            sw.set_min_content_height(120)
        except Exception:
            pass
        lbl = Gtk.Label()
        lbl.set_use_markup(True)
        lbl.set_wrap(True)
        lbl.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        lbl.set_xalign(0.0)
        lbl.set_yalign(0.0)
        lbl.set_justify(Gtk.Justification.LEFT)
        lbl.set_selectable(True)
        lbl.set_valign(Gtk.Align.START)
        lbl.set_halign(Gtk.Align.FILL)
        lbl.connect("activate-link", self._on_label_link)
        sw.set_child(lbl)
        self._content_widget = lbl
        return sw

    def _on_label_link(self, _label, uri):
        self._on_link(uri)
        return True  # never let GTK open the URI

    def _create_backend_widget(self):
        widget = None
        WebKit = _webkit()
        if WebKit:
            try:
                widget = self._create_webkit_view(WebKit)
                self._engine = "webkit"
            except Exception:
                self._logger.exception("WebKitGTK view failed; using label fallback")
                widget = None
        if widget is None:
            widget = self._create_label_view()
            self._engine = "label"

        self._backend_widget = widget
        self._apply_size_policy()
        try:
            widget.set_sensitive(bool(self._enabled))
            if self._help_text:
                widget.set_tooltip_text(self._help_text)
            widget.set_visible(self.visible())
        except Exception:
            self._logger.exception("Failed to apply initial widget state")
        self._push_content()
        self._logger.debug("_create_backend_widget: <%s> engine=%s", self.debugLabel(), self._engine)

    def _apply_size_policy(self):
        widget = getattr(self, "_backend_widget", None)
        if widget is None:
            return
        try:
            eff_h = bool(self.stretchable(YUIDimension.YD_HORIZ) or self.weight(YUIDimension.YD_HORIZ))
            eff_v = bool(self.stretchable(YUIDimension.YD_VERT) or self.weight(YUIDimension.YD_VERT))
            widget.set_hexpand(eff_h)
            widget.set_vexpand(eff_v)
            widget.set_halign(Gtk.Align.FILL if eff_h else Gtk.Align.START)
            widget.set_valign(Gtk.Align.FILL if eff_v else Gtk.Align.START)
        except Exception:
            self._logger.exception("_apply_size_policy failed")

    # -- content ------------------------------------------------------------

    def _push_content(self):
        if getattr(self, "_backend_widget", None) is None:
            return
        try:
            if self._engine == "webkit":
                self._backend_widget.load_html(self._sanitized().document, None)
            elif self._content_widget is not None:
                markup = self._text_pango()
                try:
                    self._content_widget.set_markup(markup)
                except Exception:
                    self._content_widget.set_text(
                        "\n".join("".join(seg["text"] for seg in line) for line in self._text_lines()))
        except Exception:
            self._logger.exception("Failed to show HTML content")

    def _apply_content(self):
        self._push_content()

    def _on_link(self, uri: str):
        index = self._link_index(uri)
        if index is not None:
            self._activate_link(index)

    # -- common widget API --------------------------------------------------

    def setStretchable(self, dimension, stretchable):
        super().setStretchable(dimension, stretchable)
        self._apply_size_policy()

    def _set_backend_enabled(self, enabled):
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.set_sensitive(bool(enabled))
        except Exception:
            self._logger.exception("Failed to set sensitive state")

    def setVisible(self, visible=True):
        super().setVisible(visible)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.set_visible(bool(visible))
        except Exception:
            self._logger.exception("setVisible failed")

    def setHelpText(self, help_text: str):
        super().setHelpText(help_text)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.set_tooltip_text(help_text)
        except Exception:
            self._logger.exception("setHelpText failed")
