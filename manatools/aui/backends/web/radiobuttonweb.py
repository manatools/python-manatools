"""Web backend RadioButton implementation."""
from ...yui_common import YWidget
from .commonweb import widget_attrs, escape_html, format_label_with_shortcut

class YRadioButtonWeb(YWidget):
    """Radio button widget."""
    def __init__(self, parent=None, label: str = "", isChecked: bool = False):
        super().__init__(parent)
        self._label = label
        self._checked = isChecked
        self._group_name = None
    
    def widgetClass(self):
        return "YRadioButton"
    
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
    
    def value(self) -> bool:
        return self._checked
    
    def setValue(self, checked: bool):
        self.setChecked(checked)
    
    def _get_group_name(self) -> str:
        """Get radio group name (based on parent container)."""
        if self._group_name:
            return self._group_name
        if self._parent:
            return f"radio_group_{self._parent.id()}"
        return f"radio_group_{self.id()}"
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        group_name = self._get_group_name()
        
        extra_attrs = {
            "type": "radio",
            "name": group_name,
            "checked": self._checked,
        }
        
        attrs = widget_attrs(self.id(), "YRadioButton", self._enabled, self._visible, extra_attrs=extra_attrs)
        label_html = format_label_with_shortcut(self._label)
        
        return f'''<label class="mana-radiobutton-wrapper">
    <input {attrs}>
    <span class="mana-radiobutton-label">{label_html}</span>
</label>'''
