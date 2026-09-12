"""
Web backend HBox (horizontal layout) implementation.
"""

from ...yui_common import YWidget, YUIDimension
from .commonweb import widget_attrs, layout_children_html


class YHBoxWeb(YWidget):
    """Horizontal box layout container."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stretchable_horiz = True  # HBox is horizontally stretchable by default

    def widgetClass(self):
        return "YHBox"

    def stretchable(self, dim):
        """A box stretches if any child stretches or carries a weight in *dim*."""
        for child in self._children:
            try:
                if child.stretchable(dim) or child.weight(dim):
                    return True
            except Exception:
                continue
        return super().stretchable(dim)

    def render(self) -> str:
        """Render the HBox and its children to HTML."""
        children_html = layout_children_html(self._children, YUIDimension.YD_HORIZ)

        attrs = widget_attrs(
            self.id(),
            "YHBox",
            True,
            self._visible
        )
        
        return f'<div {attrs}>{children_html}</div>'
