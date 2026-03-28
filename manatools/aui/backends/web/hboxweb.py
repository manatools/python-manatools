"""
Web backend HBox (horizontal layout) implementation.
"""

from ...yui_common import YWidget
from .commonweb import widget_attrs


class YHBoxWeb(YWidget):
    """Horizontal box layout container."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._stretchable_horiz = True  # HBox is horizontally stretchable by default
    
    def widgetClass(self):
        return "YHBox"
    
    def render(self) -> str:
        """Render the HBox and its children to HTML."""
        children_html = ""
        for child in self._children:
            children_html += child.render()
        
        attrs = widget_attrs(
            self.id(),
            "YHBox",
            True,
            self._visible
        )
        
        return f'<div {attrs}>{children_html}</div>'
