"""
Web backend Spacing implementation.
"""

from ...yui_common import YWidget, YUIDimension
from .commonweb import widget_attrs


class YSpacingWeb(YWidget):
    """Spacing/stretch widget."""
    
    def __init__(self, parent=None, dim=YUIDimension.YD_HORIZ, stretchable: bool = False, size_px: int = 0):
        super().__init__(parent)
        self._dimension = dim
        self._stretchable = stretchable
        self._size_px = max(0, int(size_px))
        
        # Set stretchability based on dimension
        if dim == YUIDimension.YD_HORIZ or dim == YUIDimension.Horizontal:
            self._stretchable_horiz = stretchable
        else:
            self._stretchable_vert = stretchable
    
    def widgetClass(self):
        return "YSpacing"
    
    def render(self) -> str:
        is_horizontal = self._dimension in (YUIDimension.YD_HORIZ, YUIDimension.Horizontal)
        
        style_parts = []
        
        if self._stretchable:
            style_parts.append("flex-grow: 1")
            if is_horizontal:
                style_parts.append(f"min-width: {self._size_px}px" if self._size_px else "min-width: 0")
            else:
                style_parts.append(f"min-height: {self._size_px}px" if self._size_px else "min-height: 0")
        else:
            if is_horizontal:
                style_parts.append(f"width: {self._size_px}px")
                style_parts.append("flex-shrink: 0")
            else:
                style_parts.append(f"height: {self._size_px}px")
                style_parts.append("flex-shrink: 0")
        
        style = "; ".join(style_parts)
        
        extra_attrs = {"style": style}
        extra_classes = "mana-hspacing" if is_horizontal else "mana-vspacing"
        
        attrs = widget_attrs(
            self.id(),
            "YSpacing",
            self._enabled,
            self._visible,
            extra_classes,
            extra_attrs
        )
        
        return f'<div {attrs}></div>'
