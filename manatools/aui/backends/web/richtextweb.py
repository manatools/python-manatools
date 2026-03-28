"""Web backend RichText implementation."""
from ...yui_common import YWidget
from .commonweb import widget_attrs, escape_html

class YRichTextWeb(YWidget):
    """Rich text display widget."""
    def __init__(self, parent=None, text: str = "", plainTextMode: bool = False):
        super().__init__(parent)
        self._text = text
        self._plain_text_mode = plainTextMode
    
    def widgetClass(self):
        return "YRichText"
    
    def text(self) -> str:
        return self._text
    
    def setText(self, text: str):
        self._text = text
        self._notify_update()
    
    def setValue(self, text: str):
        self.setText(text)
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        attrs = widget_attrs(self.id(), "YRichText", self._enabled, self._visible)
        content = escape_html(self._text) if self._plain_text_mode else self._text
        return f'<div {attrs}>{content}</div>'
