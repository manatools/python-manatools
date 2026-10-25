"""
Web backend Frame implementation.
"""

from ...yui_common import (YSingleChildContainerWidget, YProperty, YPropertySet,
                           YPropertyType)
from .commonweb import widget_attrs, escape_html, format_label_with_shortcut, schedule_update_if_open


class YFrameWeb(YSingleChildContainerWidget):
    """Frame container with optional label (fieldset)."""
    
    def __init__(self, parent=None, label: str = ""):
        super().__init__(parent)
        self._label = label
    
    def widgetClass(self):
        return "YFrame"

    def addChild(self, child):
        super().addChild(child)
        schedule_update_if_open(self)
    
    def label(self) -> str:
        return self._label
    
    def setLabel(self, label: str):
        self._label = label
        self._notify_update()
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)

    def _set_backend_enabled(self, enabled: bool):
        """Propagate enabled state to child and trigger re-render."""
        child = self.child()
        if child is not None:
            child._set_backend_enabled(enabled and child._enabled)
        self._notify_update()

    def setProperty(self, propertyName: str, val) -> bool:
        if propertyName == "label":
            self.setLabel(str(val))
            return True
        return False

    def getProperty(self, propertyName: str):
        if propertyName == "label":
            return self._label
        return None

    def propertySet(self):
        props = YPropertySet()
        props.add(YProperty("label", YPropertyType.YStringProperty))
        return props

    def stretchable(self, dim):
        """Stretch when the child stretches or carries a weight in *dim*."""
        child = self.child()
        if child is None:
            return False
        try:
            return bool(child.stretchable(dim) or child.weight(dim))
        except Exception:
            return False

    def render(self) -> str:
        attrs = widget_attrs(
            self.id(),
            "YFrame",
            self._enabled,
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
