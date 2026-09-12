"""
Web backend PushButton implementation.
"""

import logging
from typing import Optional

from ...yui_common import YWidget
from .commonweb import widget_attrs, escape_html, format_label_with_shortcut, extract_shortcut

logger = logging.getLogger("manatools.aui.web.YPushButtonWeb")


class YPushButtonWeb(YWidget):
    """Push button widget."""
    
    def __init__(self, parent=None, label: str = "", icon_name: Optional[str] = None, icon_only: bool = False):
        super().__init__(parent)
        self._label = label
        self._icon_name = icon_name
        self._icon_only = bool(icon_only)
        self._is_default = False
        self._shortcut = extract_shortcut(label)
    
    def widgetClass(self):
        return "YPushButton"
    
    def label(self) -> str:
        return self._label
    
    def setLabel(self, label: str):
        self._label = label
        self._shortcut = extract_shortcut(label)
        self._notify_update()
    
    def setDefault(self, default: bool = True):
        """Mark this button as the dialog default."""
        self._is_default = bool(default)
        # Notify dialog
        dialog = self.findDialog()
        if dialog and hasattr(dialog, 'setDefaultButton'):
            if default:
                dialog.setDefaultButton(self)
            else:
                dialog.setDefaultButton(None)
        self._notify_update()
    
    def default(self) -> bool:
        return self._is_default
    
    def setIcon(self, icon_name: str):
        """Set the button icon."""
        self._icon_name = icon_name
        self._notify_update()
    
    def icon(self) -> Optional[str]:
        return self._icon_name
    
    def _set_backend_enabled(self, enabled: bool):
        self._notify_update()

    def setVisible(self, visible: bool = True):
        self._visible = bool(visible)
        self._notify_update()

    def _notify_update(self):
        """Notify dialog that this widget needs re-render."""
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        """Render the button to HTML."""
        extra_classes = ""
        if self._is_default:
            extra_classes = "mana-default"
        if self._icon_only:
            extra_classes += " mana-icon-only"
        
        extra_attrs = {
            "data-shortcut": self._shortcut if self._shortcut else None,
        }
        
        attrs = widget_attrs(
            self.id(),
            "YPushButton",
            self._enabled,
            self._visible,
            extra_classes.strip(),
            extra_attrs
        )
        
        # Build button content
        content = ""

        # Render icon as an <img> fetched from the /icon/ endpoint.
        # onerror hides the image silently when the icon is not found on the
        # server, so the button still shows its text label as fallback.
        if self._icon_name:
            safe_name = escape_html(self._icon_name)
            content += (
                f'<img class="mana-button-icon" src="/icon/{safe_name}"'
                f' alt="{safe_name}"'
                f' onerror="this.style.display=\'none\'">'
            )

        # Always render the label text: it acts as a fallback when the icon
        # cannot be resolved, and improves accessibility in all cases.
        if self._label:
            label_html = format_label_with_shortcut(self._label)
            content += f'<span class="mana-button-label">{label_html}</span>'

        return f'<button {attrs}>{content}</button>'