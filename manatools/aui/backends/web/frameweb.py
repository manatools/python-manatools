"""
Web backend Frame implementation.
"""

from ...yui_common import YSingleChildContainerWidget
from .commonweb import widget_attrs, escape_html, format_label_with_shortcut


class YFrameWeb(YSingleChildContainerWidget):
    """Frame container with optional label (fieldset)."""
    
    def __init__(self, parent=None, label: str = ""):
        super().__init__(parent)
        self._label = label
    
    def widgetClass(self):
        return "YFrame"
    
    def label(self) -> str:
        return self._label
    
    def setLabel(self, label: str):
        self._label = label
        self._notify_update()
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        attrs = widget_attrs(
            self.id(),
            "YFrame",
            True,
            self._visible
        )
        
        # Legend (title)
        legend = ""
        if self._label:
            label_html = format_label_with_shortcut(self._label)
            legend = f'<legend class="mana-frame-legend">{label_html}</legend>'
        
        # Child content
        content = ""
        if self.child():
            content = self.child().render()
        
        return f'<fieldset {attrs}>{legend}<div class="mana-frame-content">{content}</div></fieldset>'
