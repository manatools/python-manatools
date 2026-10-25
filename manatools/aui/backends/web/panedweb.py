"""Web backend Paned implementation."""
import logging
from ...yui_common import YWidget, YUIDimension
from .commonweb import widget_attrs, schedule_update_if_open

logger = logging.getLogger("manatools.aui.web.YPanedWeb")

class YPanedWeb(YWidget):
    """Paned container with resizable split."""
    def __init__(self, parent=None, dimension=YUIDimension.YD_HORIZ):
        super().__init__(parent)
        self._dimension = dimension
    
    def widgetClass(self):
        return "YPaned"

    def addChild(self, child):
        """Add a pane; like the Qt splitter, a paned holds two children."""
        if len(self._children) >= 2:
            logger.warning("YPanedWeb can only manage two children; ignoring extra child")
            return
        super().addChild(child)
        schedule_update_if_open(self)
    
    def isHorizontal(self) -> bool:
        return self._dimension in (YUIDimension.YD_HORIZ, YUIDimension.Horizontal)
    
    def render(self) -> str:
        extra_classes = "mana-paned-horizontal" if self.isHorizontal() else "mana-paned-vertical"
        attrs = widget_attrs(self.id(), "YPaned", True, self._visible, extra_classes)

        children_html = ""
        for i, child in enumerate(self._children):
            children_html += f'<div class="mana-paned-section">{child.render()}</div>'
            if i < len(self._children) - 1:
                children_html += '<div class="mana-paned-divider"></div>'

        return f'<div {attrs}>{children_html}</div>'
