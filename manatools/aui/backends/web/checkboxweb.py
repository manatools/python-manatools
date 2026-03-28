"""
Web backend CheckBox implementation.
"""

from ...yui_common import YWidget, YCheckBoxState
from .commonweb import widget_attrs, escape_html, format_label_with_shortcut


class YCheckBoxWeb(YWidget):
    """Checkbox widget."""
    
    def __init__(self, parent=None, label: str = "", is_checked: bool = False):
        super().__init__(parent)
        self._label = label
        self._checked = is_checked
        self._tri_state = False
    
    def widgetClass(self):
        return "YCheckBox"
    
    def label(self) -> str:
        return self._label
    
    def setLabel(self, label: str):
        self._label = label
        self._notify_update()
    
    def isChecked(self) -> bool:
        return self._checked
    
    def setChecked(self, checked: bool = True):
        self._checked = bool(checked)
        self._notify_update()
    
    def value(self) -> YCheckBoxState:
        if self._checked:
            return YCheckBoxState.YCheckBox_on
        return YCheckBoxState.YCheckBox_off
    
    def setValue(self, state):
        if isinstance(state, YCheckBoxState):
            self._checked = state == YCheckBoxState.YCheckBox_on
        else:
            self._checked = bool(state)
        self._notify_update()
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        extra_attrs = {
            "type": "checkbox",
            "checked": self._checked,
        }
        
        attrs = widget_attrs(
            self.id(),
            "YCheckBox",
            self._enabled,
            self._visible,
            extra_attrs=extra_attrs
        )
        
        label_html = format_label_with_shortcut(self._label)
        
        return f'''<label class="mana-checkbox-wrapper">
    <input {attrs}>
    <span class="mana-checkbox-label">{label_html}</span>
</label>'''
