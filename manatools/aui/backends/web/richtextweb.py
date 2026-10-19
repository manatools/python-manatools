"""Web backend RichText implementation."""
from ...yui_common import YWidget
from .commonweb import widget_attrs, escape_html

class YRichTextWeb(YWidget):
    """Rich text display widget."""
    def __init__(self, parent=None, text: str = "", plainTextMode: bool = False):
        # Attributes first: addChild() on the parent may render us immediately.
        self._text = text
        self._plain_text_mode = plainTextMode
        self._last_url: str = ""
        self._auto_scroll = False
        # Set when the next update must replace the element itself (its
        # attributes changed), not only its content.
        self._full_render = False
        super().__init__(parent)

    def widgetClass(self):
        return "YRichText"

    def text(self) -> str:
        return self._text

    def setText(self, text: str):
        self._text = text
        self._notify_update()

    def setValue(self, text: str):
        self.setText(text)

    def value(self) -> str:
        return self._text

    def plainTextMode(self) -> bool:
        return bool(self._plain_text_mode)

    def setPlainTextMode(self, on: bool = True):
        self._plain_text_mode = bool(on)
        self._notify_update()

    def autoScrollDown(self) -> bool:
        return bool(self._auto_scroll)

    def setAutoScrollDown(self, on: bool = True):
        """Keep the view scrolled to the bottom when content changes."""
        self._auto_scroll = bool(on)
        self._notify_update(full=True)

    def lastActivatedUrl(self) -> str:
        return self._last_url

    def setHelpText(self, help_text: str):
        super().setHelpText(help_text)
        self._notify_update(full=True)

    def setVisible(self, visible: bool = True):
        self._visible = bool(visible)
        self._notify_update(full=True)

    def _notify_update(self, full: bool = False):
        if full:
            self._full_render = True
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)

    def _set_backend_enabled(self, enabled: bool):
        self._notify_update(full=True)

    def _content(self) -> str:
        return escape_html(self._text) if self._plain_text_mode else self._text

    def render_update(self) -> tuple:
        """Return (target, html, action) for partial DOM updates.

        Uses action="html" to replace only innerHTML of the outer div,
        leaving the div itself in the DOM.  This prevents any re-insertion
        that would cause the widget to shift position in the layout.
        Attribute changes (visibility, tooltip, enabled, auto-scroll) need
        the element itself, so they fall back to a full replace.
        """
        if self._full_render:
            self._full_render = False
            return f'#{self.id()}', self.render(), 'replace'
        return f'#{self.id()}', self._content(), 'html'

    def render(self) -> str:
        attrs = widget_attrs(self.id(), "YRichText", self._enabled, self._visible,
                             extra_attrs={"title": self.helpText() or None,
                                          "data-autoscroll": "1" if self._auto_scroll else None})
        return f'<div {attrs}>{self._content()}</div>'
