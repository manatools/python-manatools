"""Web backend CheckBoxFrame implementation."""
from ...yui_common import YSingleChildContainerWidget
from .commonweb import widget_attrs, escape_html, format_label_with_shortcut

class YCheckBoxFrameWeb(YSingleChildContainerWidget):
    """Frame with a checkbox in the legend that enables/disables content."""
    def __init__(self, parent=None, label: str = "", checked: bool = False):
        super().__init__(parent)
        self._label = label
        self._checked = checked
    
    def widgetClass(self):
        return "YCheckBoxFrame"
    
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
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        attrs = widget_attrs(self.id(), "YCheckBoxFrame", self._enabled, self._visible)
        
        checked_attr = " checked" if self._checked else ""
        label_html = format_label_with_shortcut(self._label)
        
        legend = f'''<legend class="mana-checkboxframe-legend">
            <input type="checkbox" class="mana-checkboxframe-toggle"{checked_attr}>
            <span>{label_html}</span>
        </legend>'''
        
        content = ""
        if self.child():
            content = self.child().render()
        
        disabled_class = "" if self._checked else " mana-disabled"
        return f'<fieldset {attrs}>{legend}<div class="mana-checkboxframe-content{disabled_class}">{content}</div></fieldset>'
