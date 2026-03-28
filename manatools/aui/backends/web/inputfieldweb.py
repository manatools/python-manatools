"""
Web backend InputField implementation.
"""

from ...yui_common import YSimpleInputField
from .commonweb import widget_attrs, escape_html, format_label_with_shortcut


class YInputFieldWeb(YSimpleInputField):
    """Text input field widget."""
    
    def __init__(self, parent=None, label: str = "", password_mode: bool = False):
        super().__init__(parent)
        self._label = label
        self._password_mode = password_mode
        self._value = ""
        self._input_max_length = -1
        self._valid_chars = ""
    
    def widgetClass(self):
        return "YInputField"
    
    def value(self) -> str:
        return self._value
    
    def setValue(self, text: str):
        self._value = str(text) if text else ""
        self._notify_update()
    
    def label(self) -> str:
        return self._label
    
    def setLabel(self, label: str):
        self._label = label
        self._notify_update()
    
    def setInputMaxLength(self, max_length: int):
        """Set maximum input length (-1 for unlimited)."""
        self._input_max_length = int(max_length)
        self._notify_update()
    
    def inputMaxLength(self) -> int:
        return self._input_max_length
    
    def setValidChars(self, valid_chars: str):
        """Set valid characters for input validation."""
        self._valid_chars = valid_chars
    
    def validChars(self) -> str:
        return self._valid_chars
    
    def isPasswordMode(self) -> bool:
        return self._password_mode
    
    def _notify_update(self):
        """Notify dialog that this widget needs re-render."""
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        """Render the input field to HTML."""
        input_type = "password" if self._password_mode else "text"
        
        extra_attrs = {
            "type": input_type,
            "value": self._value,
        }
        
        if self._input_max_length > 0:
            extra_attrs["maxlength"] = str(self._input_max_length)
        
        if self._valid_chars:
            # Create pattern from valid chars
            extra_attrs["pattern"] = f"[{escape_html(self._valid_chars)}]*"
        
        attrs = widget_attrs(
            self.id(),
            "YInputField",
            self._enabled,
            self._visible,
            extra_attrs=extra_attrs
        )
        
        # Build with label if present
        html = ""
        if self._label:
            label_html = format_label_with_shortcut(self._label)
            label_id = f"{self.id()}_label"
            html += f'<label id="{label_id}" class="mana-inputfield-label" for="{self.id()}_input">{label_html}</label>'
        
        # Replace id in attrs for the input element
        input_attrs = attrs.replace(f'id="{self.id()}"', f'id="{self.id()}_input" data-widget-id="{self.id()}"')
        html += f'<input {input_attrs}>'
        
        # Wrap in container
        container_attrs = widget_attrs(
            self.id(),
            "YInputField",
            self._enabled,
            self._visible,
            "mana-inputfield-container"
        )
        
        return f'<div {container_attrs}>{html}</div>'
