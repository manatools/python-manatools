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
from gi.repository import Gtk, Pango, GLib, Gdk
import logging
import re
from ...yui_common import *



class _YRichTextMeasureScrolledWindow(Gtk.ScrolledWindow):
    """Gtk.ScrolledWindow subclass delegating size measurement to YRichTextGtk."""

    def __init__(self, owner):
        """Initialize the measuring scrolled window.

        Args:
            owner: Owning YRichTextGtk instance.
        """
        super().__init__()
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
            self._owner._logger.exception("RichText backend do_measure delegation failed", exc_info=True)
            return (0, 0, -1, -1)


class YRichTextGtk(YWidget):
    """GTK4 rich text widget with plain/markup rendering and link activation."""

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

    # --- size policy helpers ---
    def setStretchable(self, dimension, stretchable):
        """Override stretchable to immediately re-apply the GTK size policy."""
        try:
            # Call parent implementation first
            super().setStretchable(dimension, stretchable)
        except Exception:
            self._logger.exception("setStretchable: base implementation failed")
        # Apply to current backend/content
        self._apply_size_policy()

    def _apply_size_policy(self):
        """Apply GTK4 expand and alignment based on stretch flags and weights.

        - Stretch or positive weight => expand True and FILL.
        - Otherwise => expand False and START.
        - Applies to the Gtk.ScrolledWindow and content widget (Label/TextView).
        """
        try:
            h_stretch = bool(self.stretchable(YUIDimension.YD_HORIZ))
            v_stretch = bool(self.stretchable(YUIDimension.YD_VERT))
            try:
                w_h = float(self.weight(YUIDimension.YD_HORIZ))
            except Exception:
                w_h = 0.0
            try:
                w_v = float(self.weight(YUIDimension.YD_VERT))
            except Exception:
                w_v = 0.0

            eff_h = bool(h_stretch or (w_h > 0.0))
            eff_v = bool(v_stretch or (w_v > 0.0))

            targets = []
            if getattr(self, "_backend_widget", None) is not None:
                targets.append(self._backend_widget)
            if getattr(self, "_content_widget", None) is not None:
                targets.append(self._content_widget)

            for ww in targets:
                try:
                    ww.set_hexpand(eff_h)
                except Exception:
                    self._logger.debug("set_hexpand failed on %s", type(ww), exc_info=True)
                try:
                    ww.set_halign(Gtk.Align.FILL if eff_h else Gtk.Align.START)
                except Exception:
                    self._logger.debug("set_halign failed on %s", type(ww), exc_info=True)
                try:
                    ww.set_vexpand(eff_v)
                except Exception:
                    self._logger.debug("set_vexpand failed on %s", type(ww), exc_info=True)
                try:
                    ww.set_valign(Gtk.Align.FILL if eff_v else Gtk.Align.START)
                except Exception:
                    self._logger.debug("set_valign failed on %s", type(ww), exc_info=True)

            # Enforce left/top content alignment for Label/TextView
            try:
                cw = getattr(self, "_content_widget", None)
                if isinstance(cw, Gtk.Label):
                    cw.set_justify(Gtk.Justification.LEFT)
                    cw.set_xalign(0.0)
                elif isinstance(cw, Gtk.TextView):
                    cw.set_monospace(False)
                    cw.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            except Exception:
                self._logger.debug("additional content alignment failed", exc_info=True)

            self._logger.debug(
                "_apply_size_policy: h_stretch=%s v_stretch=%s w_h=%s w_v=%s eff_h=%s eff_v=%s",
                h_stretch, v_stretch, w_h, w_v, eff_h, eff_v
            )
        except Exception:
            self._logger.exception("_apply_size_policy: unexpected failure")

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
                    self._logger.debug("set_use_markup failed on Gtk.Label", exc_info=True)
                # Convert common HTML tags to Pango markup supported by Gtk.Label
                converted = self._html_to_pango_markup(self._text)
                try:
                    w.set_markup(converted)
                except Exception as e:
                    # If markup fails, log and fallback to plain text
                    self._logger.error("set_markup failed; falling back to set_text: %s", e, exc_info=True)
                    try:
                        w.set_text(re.sub(r"<[^>]+>", "", converted))
                    except Exception:
                        self._logger.debug("set_text failed on Gtk.Label", exc_info=True)
        except Exception:
            self._logger.exception("setValue failed", exc_info=True)

    def value(self) -> str:
        return self._text

    def plainTextMode(self) -> bool:
        return bool(self._plain)

    def setPlainTextMode(self, on: bool = True):
        self._plain = bool(on)
        # rebuild content widget to reflect mode
        if getattr(self, "_backend_widget", None) is not None:
            self._create_content()
            self._apply_size_policy()
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

    def do_measure(self, orientation, for_size):
        """GTK4 virtual method for size measurement.

        Args:
            orientation: Gtk.Orientation (HORIZONTAL or VERTICAL)
            for_size: Size in the opposite orientation (-1 if not constrained)

        Returns:
            tuple: (minimum_size, natural_size, minimum_baseline, natural_baseline)
        """
        widget = getattr(self, "_backend_widget", None)
        if widget is not None:
            try:
                minimum_size, natural_size, minimum_baseline, natural_baseline = Gtk.ScrolledWindow.do_measure(widget, orientation, for_size)
                if orientation == Gtk.Orientation.HORIZONTAL:
                    minimum_baseline = -1
                    natural_baseline = -1
                measured = (minimum_size, natural_size, minimum_baseline, natural_baseline)
                self._logger.debug("RichText do_measure orientation=%s for_size=%s -> %s", orientation, for_size, measured)
                return measured
            except Exception:
                self._logger.exception("RichText base do_measure failed", exc_info=True)

        text = str(getattr(self, "_text", "") or "")
        line_count = max(1, text.count("\n") + 1)
        longest_line = max((len(line) for line in text.splitlines()), default=len(text))
        if orientation == Gtk.Orientation.HORIZONTAL:
            minimum_size = 160
            natural_size = max(minimum_size, min(900, max(220, longest_line * 7)))
        else:
            minimum_size = max(72, min(240, line_count * 18))
            natural_size = max(minimum_size, min(720, line_count * 22))
        self._logger.debug(
            "RichText fallback do_measure orientation=%s for_size=%s -> min=%s nat=%s",
            orientation,
            for_size,
            minimum_size,
            natural_size,
        )
        return (minimum_size, natural_size, -1, -1)

    def _create_content(self):
        # Create the content widget according to mode
        try:
            if self._plain:
                tv = Gtk.TextView()
                try:
                    tv.set_editable(False)
                except Exception:
                    self._logger.debug("set_editable failed on Gtk.TextView", exc_info=True)
                try:
                    tv.set_cursor_visible(False)
                except Exception:
                    self._logger.debug("set_cursor_visible failed on Gtk.TextView", exc_info=True)
                try:
                    tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
                except Exception:
                    self._logger.debug("set_wrap_mode failed on Gtk.TextView", exc_info=True)
                self._content_widget = tv
                # set initial text
                try:
                    buf = tv.get_buffer()
                    buf.set_text(self._text)
                except Exception:
                    self._logger.debug("set_text failed on Gtk.TextBuffer", exc_info=True)
            else:
                lbl = Gtk.Label()
                try:
                    lbl.set_use_markup(True)
                except Exception:
                    self._logger.debug("set_use_markup failed on Gtk.Label", exc_info=True)
                # Convert HTML to Pango markup for GTK Label
                converted = self._html_to_pango_markup(self._text)
                try:
                    lbl.set_markup(converted)
                except Exception:
                    self._logger.exception("set_markup failed on Gtk.Label", exc_info=True)
                    lbl.set_text(converted)
                try:
                    lbl.set_selectable(False)  # keep it non-selectable; avoids odd sizing in some themes
                except Exception:
                    self._logger.exception("set_selectable failed on Gtk.Label", exc_info=True) 
                try:
                    lbl.set_wrap(True)
                    lbl.set_wrap_mode(Pango.WrapMode.WORD_CHAR) # need Pango.WrapMode
                    lbl.set_xalign(0.0)
                    lbl.set_justify(Gtk.Justification.LEFT)
                except Exception:
                    self._logger.debug("set_justify failed on Gtk.Label", exc_info=True)
                # connect link activation
                def _on_activate_link(label, uri):
                    try:
                        self._last_url = uri
                        dlg = self.findDialog()
                        if dlg and self.notify():
                            # emit a MenuEvent for link activation (back-compat)
                            dlg._post_event(YMenuEvent(item=None, id=uri))
                    except Exception:
                        self._logger.debug("activate-link handler failed", exc_info=True)
                    # return True to stop default handling
                    return True
                try:
                    lbl.connect("activate-link", _on_activate_link)
                except Exception:
                    self._logger.debug("connect activate-link failed on Gtk.Label", exc_info=True)
                self._content_widget = lbl
        except Exception:
            self._logger.exception("Failed to create content widget", exc_info=True)
            # fallback to a simple label
            self._content_widget = Gtk.Label(label=self._text)

    def _create_backend_widget(self):
        """Create scrolled backend and attach rich text content widget."""
        sw = _YRichTextMeasureScrolledWindow(self)
        try:
            # let size policy decide final expand/align; start with sane defaults
            sw.set_hexpand(True)
            sw.set_vexpand(True)
            sw.set_halign(Gtk.Align.FILL)
            sw.set_valign(Gtk.Align.FILL)
        except Exception:
            self._logger.debug("Failed to set initial expand/align on scrolled window", exc_info=True)

        self._create_content()
        try:
            sw.set_child(self._content_widget)
        except Exception:
            try:
                sw.add(self._content_widget)
            except Exception:
                self._logger.debug("Failed to attach content to scrolled window", exc_info=True)
        self._backend_widget = sw

        # Apply consistent size policy after backend and content exist
        self._apply_size_policy()

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
        Supports: h1-h6 (as bold spans with size), b/i/em/u, a href, p/br, ul/li.
        Unknown tags are stripped.
        """
        self._logger.debug("Converted markup: %s", s)
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
        # Explicitly convert formatting tags to Pango span attributes
        t = re.sub(r"<b\s*>", "<span weight=\"bold\">", t, flags=re.IGNORECASE)
        t = re.sub(r"</b\s*>", "</span>", t, flags=re.IGNORECASE)
        t = re.sub(r"<i\s*>", "<span style=\"italic\">", t, flags=re.IGNORECASE)
        t = re.sub(r"</i\s*>", "</span>", t, flags=re.IGNORECASE)
        t = re.sub(r"<em\s*>", "<span style=\"italic\">", t, flags=re.IGNORECASE)
        t = re.sub(r"</em\s*>", "</span>", t, flags=re.IGNORECASE)
        t = re.sub(r"<u\s*>", "<span underline=\"single\">", t, flags=re.IGNORECASE)
        t = re.sub(r"</u\s*>", "</span>", t, flags=re.IGNORECASE)
        # Allow basic formatting tags and <a href>; strip all other tags
        t = re.sub(r"</?(?!span\b|a\b)[a-zA-Z0-9]+\b[^>]*>", "", t)

        self._logger.debug("Converted markup: %s", t)
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
