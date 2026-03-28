"""Web backend Paned implementation."""
from ...yui_common import YWidget, YUIDimension
from .commonweb import widget_attrs

class YPanedWeb(YWidget):
    """Paned container with resizable split."""
    def __init__(self, parent=None, dimension=YUIDimension.YD_HORIZ):
        super().__init__(parent)
        self._dimension = dimension
    
    def widgetClass(self):
        return "YPaned"
    
    def isHorizontal(self) -> bool:
        return self._dimension in (YUIDimension.YD_HORIZ, YUIDimension.Horizontal)
    
    def render(self) -> str:
        direction = "row" if self.isHorizontal() else "column"
        extra_classes = "mana-paned-horizontal" if self.isHorizontal() else "mana-paned-vertical"
        
        extra_attrs = {
            "style": f"display: flex; flex-direction: {direction};",
        }
        
        attrs = widget_attrs(self.id(), "YPaned", True, self._visible, extra_classes, extra_attrs)
        
        children_html = ""
        for i, child in enumerate(self._children):
            children_html += f'<div class="mana-paned-section" style="flex: 1;">{child.render()}</div>'
            if i < len(self._children) - 1:
                children_html += '<div class="mana-paned-divider"></div>'
        
        return f'<div {attrs}>{children_html}</div>'
