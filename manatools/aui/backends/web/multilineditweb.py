"""Web backend MultiLineEdit implementation."""
from ...yui_common import YWidget
from .commonweb import widget_attrs, escape_html, format_label_with_shortcut

class YMultiLineEditWeb(YWidget):
    """Multi-line text editor widget."""
    def __init__(self, parent=None, label: str = ""):
        super().__init__(parent)
        self._label = label
        self._value = ""
        self._input_max_length = -1
    
    def widgetClass(self):
        return "YMultiLineEdit"
    
    def label(self) -> str:
        return self._label
    
    def setLabel(self, label: str):
        self._label = label
        self._notify_update()
    
    def value(self) -> str:
        return self._value
    
    def setValue(self, text: str):
        self._value = str(text) if text else ""
        self._notify_update()
    
    def setInputMaxLength(self, max_length: int):
        self._input_max_length = int(max_length)
    
    def inputMaxLength(self) -> int:
        return self._input_max_length
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        extra_attrs = {}
        if self._input_max_length > 0:
            extra_attrs["maxlength"] = str(self._input_max_length)
        
        attrs = widget_attrs(self.id(), "YMultiLineEdit", self._enabled, self._visible, extra_attrs=extra_attrs)
        
        html = ""
        if self._label:
            label_html = format_label_with_shortcut(self._label)
            html += f'<label class="mana-multilineedit-label">{label_html}</label>'
        
        html += f'<textarea {attrs}>{escape_html(self._value)}</textarea>'
        return f'<div class="mana-multilineedit-container">{html}</div>'
