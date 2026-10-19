"""
Web backend Alignment implementation.
"""

from ...yui_common import YSingleChildContainerWidget, YAlignmentType, YUIDimension
from .commonweb import widget_attrs, schedule_update_if_open


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

    def addChild(self, child):
        super().addChild(child)
        schedule_update_if_open(self)
    
    def setMinWidth(self, min_width: int):
        self._min_width = max(0, int(min_width))
    
    def setMinHeight(self, min_height: int):
        self._min_height = max(0, int(min_height))
    
    def setMinSize(self, min_width: int, min_height: int):
        self.setMinWidth(min_width)
        self.setMinHeight(min_height)

    def setAlignment(self, horAlign=YAlignmentType.YAlignUnchanged,
                     vertAlign=YAlignmentType.YAlignUnchanged):
        self._hor_align = horAlign
        self._vert_align = vertAlign
        self._notify_update()

    def stretchable(self, dim):
        """Same rule as the Qt backend: centering or end alignment needs the
        free space, otherwise follow the child's stretch or weight."""
        if dim == YUIDimension.YD_HORIZ and self._hor_align in (
                YAlignmentType.YAlignEnd, YAlignmentType.YAlignCenter):
            return True
        if dim == YUIDimension.YD_VERT and self._vert_align == YAlignmentType.YAlignCenter:
            return True
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
