"""Web backend ReplacePoint implementation."""
from ...yui_common import YSingleChildContainerWidget
from .commonweb import widget_attrs, schedule_update_if_open

class YReplacePointWeb(YSingleChildContainerWidget):
    """Replace point - container that can swap its child dynamically."""
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def widgetClass(self):
        return "YReplacePoint"

    def addChild(self, child):
        super().addChild(child)
        schedule_update_if_open(self)
    
    def showChild(self):
        """Show the current child."""
        if self.child():
            self.child().setVisible(True)
        self._notify_update()
    
    def deleteChildren(self):
        """Remove all children."""
        super().deleteChildren()
        self._notify_update()

    def stretchable(self, dim):
        """Stretch when the child stretches or carries a weight in *dim*."""
        child = self.child()
        if child is None:
            return False
        try:
            return bool(child.stretchable(dim) or child.weight(dim))
        except Exception:
            return False
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        attrs = widget_attrs(self.id(), "YReplacePoint", self._enabled, self._visible)
        content = self.child().render() if self.child() else ""
        return f'<div {attrs}>{content}</div>'
