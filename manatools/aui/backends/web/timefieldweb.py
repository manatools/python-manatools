"""Web backend TimeField implementation."""
from ...yui_common import YWidget
from .commonweb import widget_attrs, escape_html, format_label_with_shortcut

class YTimeFieldWeb(YWidget):
    """Time input field widget."""
    def __init__(self, parent=None, label: str = ""):
        super().__init__(parent)
        self._label = label
        self._value = ""  # Format: HH:MM
    
    def widgetClass(self):
        return "YTimeField"
    
    def label(self) -> str:
        return self._label
    
    def setLabel(self, label: str):
        self._label = label
        self._notify_update()
    
    def value(self) -> str:
        return self._value
    
    def setValue(self, val: str):
        self._value = str(val) if val else ""
        self._notify_update()
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        extra_attrs = {
            "type": "time",
            "value": self._value,
        }
        
        attrs = widget_attrs(self.id(), "YTimeField", self._enabled, self._visible, extra_attrs=extra_attrs)
        
        html = ""
        if self._label:
            label_html = format_label_with_shortcut(self._label)
            html += f'<label class="mana-timefield-label">{label_html}</label>'
        
        html += f'<input {attrs}>'
        return f'<div class="mana-timefield-container">{html}</div>'
