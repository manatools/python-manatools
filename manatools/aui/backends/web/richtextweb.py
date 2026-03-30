"""Web backend RichText implementation."""
from ...yui_common import YWidget
from .commonweb import widget_attrs, escape_html

class YRichTextWeb(YWidget):
    """Rich text display widget."""
    def __init__(self, parent=None, text: str = "", plainTextMode: bool = False):
        super().__init__(parent)
        self._text = text
        self._plain_text_mode = plainTextMode
        self._last_url: str = ""
    
    def widgetClass(self):
        return "YRichText"
    
    def text(self) -> str:
        return self._text
    
    def setText(self, text: str):
        self._text = text
        self._notify_update()
    
    def setValue(self, text: str):
        self.setText(text)

    def lastActivatedUrl(self) -> str:
        return self._last_url
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render_update(self) -> tuple:
        """Return (target, html, action) for partial DOM updates.

        Uses action="html" to replace only innerHTML of the outer div,
        leaving the div itself in the DOM.  This prevents any re-insertion
        that would cause the widget to shift position in the layout.
        """
        content = escape_html(self._text) if self._plain_text_mode else self._text
        return f'#{self.id()}', content, 'html'

    def render(self) -> str:
        attrs = widget_attrs(self.id(), "YRichText", self._enabled, self._visible)
        content = escape_html(self._text) if self._plain_text_mode else self._text
        return f'<div {attrs}>{content}</div>'
