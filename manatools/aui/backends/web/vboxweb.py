"""
Web backend VBox (vertical layout) implementation.
"""

from ...yui_common import YWidget
from .commonweb import widget_attrs


class YVBoxWeb(YWidget):
    """Vertical box layout container."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._stretchable_vert = True  # VBox is vertically stretchable by default
    
    def widgetClass(self):
        return "YVBox"
    
    def render(self) -> str:
        """Render the VBox and its children to HTML."""
        children_html = ""
        for child in self._children:
            children_html += child.render()
        
        attrs = widget_attrs(
            self.id(),
            "YVBox",
            True,
            self._visible
        )
        
        return f'<div {attrs}>{children_html}</div>'
