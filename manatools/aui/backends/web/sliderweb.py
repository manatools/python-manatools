"""Web backend Slider implementation."""
from ...yui_common import YWidget
from .commonweb import widget_attrs, escape_html, format_label_with_shortcut

class YSliderWeb(YWidget):
    """Slider input widget."""
    def __init__(self, parent=None, label: str = "", minVal: int = 0, maxVal: int = 100, initialVal: int = 0):
        super().__init__(parent)
        self._label = label
        self._min_val = minVal
        self._max_val = maxVal
        self._value = max(minVal, min(initialVal, maxVal))
    
    def widgetClass(self):
        return "YSlider"
    
    def label(self) -> str:
        return self._label
    
    def setLabel(self, label: str):
        self._label = label
        self._notify_update()
    
    def value(self) -> int:
        return self._value
    
    def setValue(self, val):
        val = int(val) if val is not None else self._min_val
        self._value = max(self._min_val, min(val, self._max_val))
        self._notify_update()
    
    def minValue(self) -> int:
        return self._min_val
    
    def maxValue(self) -> int:
        return self._max_val
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        extra_attrs = {
            "type": "range",
            "min": str(self._min_val),
            "max": str(self._max_val),
            "value": str(self._value),
        }
        
        attrs = widget_attrs(self.id(), "YSlider", self._enabled, self._visible, extra_attrs=extra_attrs)
        
        html = ""
        if self._label:
            label_html = format_label_with_shortcut(self._label)
            html += f'<label class="mana-slider-label">{label_html}</label>'
        
        html += f'<input {attrs}>'
        html += f'<span class="mana-slider-value">{self._value}</span>'
        return f'<div class="mana-slider-container">{html}</div>'
