"""
Web backend Alignment implementation.
"""

from ...yui_common import YSingleChildContainerWidget, YAlignmentType
from .commonweb import widget_attrs


class YAlignmentWeb(YSingleChildContainerWidget):
    """Alignment container widget."""
    
    def __init__(self, parent=None, horAlign=YAlignmentType.YAlignUnchanged, vertAlign=YAlignmentType.YAlignUnchanged):
        super().__init__(parent)
        self._hor_align = horAlign
        self._vert_align = vertAlign
        self._min_width = 0
        self._min_height = 0
    
    def widgetClass(self):
        return "YAlignment"
    
    def setMinWidth(self, min_width: int):
        self._min_width = max(0, int(min_width))
    
    def setMinHeight(self, min_height: int):
        self._min_height = max(0, int(min_height))
    
    def setMinSize(self, min_width: int, min_height: int):
        self.setMinWidth(min_width)
        self.setMinHeight(min_height)
    
    def render(self) -> str:
        # Map alignment to CSS
        align_map = {
            YAlignmentType.YAlignUnchanged: "stretch",
            YAlignmentType.YAlignBegin: "flex-start",
            YAlignmentType.YAlignEnd: "flex-end",
            YAlignmentType.YAlignCenter: "center",
        }
        
        h_align = align_map.get(self._hor_align, "stretch")
        v_align = align_map.get(self._vert_align, "stretch")
        
        style_parts = [
            f"justify-content: {h_align}",
            f"align-items: {v_align}",
        ]
        
        if self._min_width > 0:
            style_parts.append(f"min-width: {self._min_width}px")
        if self._min_height > 0:
            style_parts.append(f"min-height: {self._min_height}px")
        
        style = "; ".join(style_parts)
        
        extra_attrs = {"style": style}
        
        attrs = widget_attrs(
            self.id(),
            "YAlignment",
            True,
            self._visible,
            extra_attrs=extra_attrs
        )
        
        content = ""
        if self.child():
            content = self.child().render()
        
        return f'<div {attrs}>{content}</div>'
