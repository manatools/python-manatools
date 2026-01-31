# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
GTK4 backend RichText widget.

- Plain text mode: Gtk.TextView (read-only) inside Gtk.ScrolledWindow
- Rich text mode: Gtk.Label with markup inside Gtk.ScrolledWindow
- Link activation: emits YMenuEvent with URL id
- Auto scroll down: applies to TextView; for Label, scrolled window shows full content
'''
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, GLib, Gdk
import logging
import re
from ...yui_common import *


class YRichTextGtk(YWidget):
    def __init__(self, parent=None, text: str = "", plainTextMode: bool = False):
        super().__init__(parent)
        self._text = text or ""
        self._plain = bool(plainTextMode)
        self._auto_scroll = False
        self._last_url = None
        self._backend_widget = None
        self._content_widget = None  # TextView or Label
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        # Default: richtext should be stretchable both horizontally and vertically
        try:
            self.setStretchable(YUIDimension.YD_HORIZ, True)
            self.setStretchable(YUIDimension.YD_VERT, True)
        except Exception:
            pass

    def widgetClass(self):
        return "YRichText"

    def setValue(self, newValue: str):
        self._text = newValue or ""
        w = getattr(self, "_content_widget", None)
        if w is None:
            return
        try:
            if isinstance(w, Gtk.TextView):
                buf = w.get_buffer()
                if buf:
                    try:
                        buf.set_text(self._text)
                    except Exception:
                        pass
                if self._auto_scroll:
                    try:
                        itr_end = buf.get_end_iter()
                        w.scroll_to_iter(itr_end, 0.0, True, 0.0, 1.0)
                    except Exception:
                        pass
            elif isinstance(w, Gtk.Label):
                try:
                    w.set_use_markup(True)
                except Exception:
                    pass
                # Convert common HTML tags to Pango markup supported by Gtk.Label
                converted = self._html_to_pango_markup(self._text)
                try:
                    w.set_markup(converted)
                except Exception:
                    try:
                        w.set_text(converted)
                    except Exception:
                        pass
        except Exception:
            pass

    def value(self) -> str:
        return self._text

    def plainTextMode(self) -> bool:
        return bool(self._plain)

    def setPlainTextMode(self, on: bool = True):
        self._plain = bool(on)
        # rebuild content widget to reflect mode
        if getattr(self, "_backend_widget", None) is not None:
            self._create_content()
            self.setValue(self._text)

    def autoScrollDown(self) -> bool:
        return bool(self._auto_scroll)

    def setAutoScrollDown(self, on: bool = True):
        self._auto_scroll = bool(on)
        # apply immediately for TextView
        if self._auto_scroll and isinstance(getattr(self, "_content_widget", None), Gtk.TextView):
            try:
                buf = self._content_widget.get_buffer()
                itr_end = buf.get_end_iter()
                self._content_widget.scroll_to_iter(itr_end, 0.0, True, 0.0, 1.0)
            except Exception:
                pass

    def lastActivatedUrl(self):
        return self._last_url

    def _create_content(self):
        # Create the content widget according to mode
        try:
            if self._plain:
                tv = Gtk.TextView()
                try:
                    tv.set_editable(False)
                except Exception:
                    pass
                try:
                    tv.set_cursor_visible(False)
                except Exception:
                    pass
                try:
                    tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
                except Exception:
                    pass
                self._content_widget = tv
                # set initial text
                try:
                    buf = tv.get_buffer()
                    buf.set_text(self._text)
                except Exception:
                    pass
            else:
                lbl = Gtk.Label()
                try:
                    lbl.set_use_markup(True)
                except Exception:
                    pass
                # Convert HTML to Pango markup for GTK Label
                converted = self._html_to_pango_markup(self._text)
                try:
                    lbl.set_markup(converted)
                except Exception:
                    lbl.set_text(converted)
                try:
                    lbl.set_selectable(False)
                except Exception:
                    pass
                try:
                    lbl.set_wrap(True)
                    lbl.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
                    lbl.set_xalign(0.0)
                except Exception:
                    pass
                # connect link activation
                def _on_activate_link(label, uri):
                    try:
                        self._last_url = uri
                        dlg = self.findDialog()
                        if dlg and self.notify():
                            # emit a MenuEvent for link activation (back-compat)
                            dlg._post_event(YMenuEvent(item=None, id=uri))
                    except Exception:
                        pass
                    # return True to stop default handling
                    return True
                try:
                    lbl.connect("activate-link", _on_activate_link)
                except Exception:
                    pass
                self._content_widget = lbl
        except Exception:
            # fallback to a simple label
            self._content_widget = Gtk.Label(label=self._text)

    def _create_backend_widget(self):
        sw = Gtk.ScrolledWindow()
        try:
            sw.set_hexpand(True)
            sw.set_vexpand(True)
            try:
                sw.set_halign(Gtk.Align.FILL)
                sw.set_valign(Gtk.Align.FILL)
            except Exception:
                pass
        except Exception:
            pass

        self._create_content()
        try:
            sw.set_child(self._content_widget)
        except Exception:
            try:
                sw.add(self._content_widget)
            except Exception:
                pass
        self._backend_widget = sw
        # respect initial enabled state
        try:
            self._backend_widget.set_sensitive(bool(self._enabled))
        except Exception:
            self._logger.error("Failed to set backend widget sensitive state", exc_info=True)
        if self._help_text:
            try:
                self._backend_widget.set_tooltip_text(self._help_text)
            except Exception:
                self._logger.error("Failed to set tooltip text on backend widget", exc_info=True)
        try:
            self._backend_widget.set_visible(self.visible())
        except Exception:
            self._logger.error("Failed to set backend widget visible", exc_info=True)
        try:
            self._backend_widget.set_sensitive(self._enabled)
        except Exception:
            self._logger.exception("Failed to set sensitivity on backend widget")
        self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        
    def _set_backend_enabled(self, enabled):
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.set_sensitive(bool(enabled))
        except Exception:
            self._logger.exception("Failed to set enabled state", exc_info=True)

    def _html_to_pango_markup(self, s: str) -> str:
        """Convert a limited subset of HTML into GTK/Pango markup.
        Supports: h1-h6 (as bold spans with size), b/i/u, a href, p/br, ul/li.
        Unknown tags are stripped.
        """
        if not s:
            return ""
        t = s
        # Normalize newlines for paragraphs and breaks
        t = re.sub(r"<br\s*/?>", "\n", t, flags=re.IGNORECASE)
        t = re.sub(r"</p\s*>", "\n\n", t, flags=re.IGNORECASE)
        t = re.sub(r"<p\s*>", "", t, flags=re.IGNORECASE)
        # Lists
        t = re.sub(r"<ul\s*>", "\n", t, flags=re.IGNORECASE)
        t = re.sub(r"</ul\s*>", "\n", t, flags=re.IGNORECASE)
        t = re.sub(r"<ol\s*>", "\n", t, flags=re.IGNORECASE)
        t = re.sub(r"</ol\s*>", "\n", t, flags=re.IGNORECASE)
        t = re.sub(r"<li\s*>", "• ", t, flags=re.IGNORECASE)
        t = re.sub(r"</li\s*>", "\n", t, flags=re.IGNORECASE)
        # Headings -> bold span with size   
        sizes = {1: "xx-large", 2: "x-large", 3: "large", 4: "medium", 5: "small", 6: "x-small"}
        for n, sz in sizes.items():
            t = re.sub(fr"<h{n}\s*>", f"<span weight=\"bold\" size=\"{sz}\">", t, flags=re.IGNORECASE)
            t = re.sub(fr"</h{n}\s*>", "</span>\n", t, flags=re.IGNORECASE)
        # Allow basic formatting tags and <a href>; strip all other tags
        t = re.sub(r"</?(?!span\b|a\b|b\b|i\b|u\b)[a-zA-Z0-9]+\b[^>]*>", "", t)
        return t

    def setVisible(self, visible=True):
        super().setVisible(visible)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.set_visible(visible)
        except Exception:
            self._logger.exception("setVisible failed", exc_info=True)

    def setHelpText(self, help_text: str):
        super().setHelpText(help_text)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.set_tooltip_text(help_text)
        except Exception:
            self._logger.exception("setHelpText failed", exc_info=True)
