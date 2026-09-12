"""Web backend ReplacePoint implementation."""
from ...yui_common import YSingleChildContainerWidget
from .commonweb import widget_attrs

class YReplacePointWeb(YSingleChildContainerWidget):
    """Replace point - container that can swap its child dynamically."""
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def widgetClass(self):
        return "YReplacePoint"
    
    def showChild(self):
        """Show the current child."""
        if self.child():
            self.child().setVisible(True)
        self._notify_update()
    
    def deleteChildren(self):
        """Remove all children."""
        super().deleteChildren()
        self._notify_update()
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        attrs = widget_attrs(self.id(), "YReplacePoint", self._enabled, self._visible)
        content = self.child().render() if self.child() else ""
        return f'<div {attrs}>{content}</div>'
