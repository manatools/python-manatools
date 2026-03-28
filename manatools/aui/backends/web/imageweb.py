"""Web backend Image implementation."""
from ...yui_common import YWidget
from .commonweb import widget_attrs, escape_html

class YImageWeb(YWidget):
    """Image display widget."""
    def __init__(self, parent=None, imageFileName: str = ""):
        super().__init__(parent)
        self._image_file = imageFileName
        self._alt_text = ""
    
    def widgetClass(self):
        return "YImage"
    
    def imageFileName(self) -> str:
        return self._image_file
    
    def setImage(self, imageFileName: str):
        self._image_file = imageFileName
        self._notify_update()
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        extra_attrs = {
            "src": self._image_file,
            "alt": self._alt_text or "Image",
        }
        
        attrs = widget_attrs(self.id(), "YImage", self._enabled, self._visible, extra_attrs=extra_attrs)
        return f'<img {attrs}>'
