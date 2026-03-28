"""
Web backend ProgressBar implementation.
Author: Matteo Pasotti <xquiet@coriolite.com>
License: LGPLv2+
"""
from ...yui_common import YWidget
from .commonweb import escape_html


class YProgressBarWeb(YWidget):
    """Progress bar widget."""

    def __init__(self, parent=None, label: str = "", max_value: int = 100):
        super().__init__(parent)
        self._label = label
        self._max_value = max_value
        self._value = 0

    def widgetClass(self):
        return "YProgressBar"

    def label(self) -> str:
        return self._label

    def setLabel(self, label: str):
        self._label = label
        self._notify_update()

    def value(self) -> int:
        return self._value

    def setValue(self, value: int):
        self._value = max(0, min(int(value), self._max_value))
        self._notify_update()

    def maxValue(self) -> int:
        return self._max_value

    def setMaxValue(self, max_val: int):
        self._max_value = max(1, int(max_val))
        self._notify_update()

    def _set_backend_enabled(self, enabled: bool):
        self._notify_update()

    def setVisible(self, visible: bool = True):
        self._visible = bool(visible)
        self._notify_update()

    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)

    def render_update(self) -> tuple:
        """Return (target_selector, html) for partial DOM updates.

        Called by _flush_update instead of render() so that only the inner div
        is replaced, leaving the label untouched.

        Returns:
            A tuple of (css_selector, html_snippet) where css_selector targets
            only the inner progress div and html_snippet is its new content.
        """
        widget_id = self.id()
        percent = (self._value / self._max_value * 100) if self._max_value > 0 else 0

        visible_style = "" if self._visible else ' style="display:none"'
        enabled_attr = "" if self._enabled else " disabled"

        inner_html = (
            f'<div id="{widget_id}"'
            f' class="mana-progressbar-inner"'
            f' data-widget-class="YProgressBar"'
            f' data-value="{self._value}"'
            f' data-max="{self._max_value}"'
            f'{visible_style}>'
            f'<progress value="{self._value}" max="{self._max_value}"'
            f'{enabled_attr}>{percent:.0f}%</progress>'
            f'<span class="mana-progressbar-text">{percent:.0f}%</span>'
            f'</div>'
        )

        return f'#{widget_id}', inner_html

    def render(self) -> str:
        """Full initial render: static label + dynamic inner div.

        Structure:
            <div class="mana-progressbar-container">   <- no id, no data-container-for
                <label>...</label>                      <- static, never replaced
                <div id="{widget_id}" ...>              <- render_update() targets this
                    <progress .../>
                    <span>...</span>
                </div>
            </div>

        On subsequent setValue() calls, _flush_update uses render_update()
        which replaces only the inner div via #id, leaving the label intact.
        Do NOT add data-container-for to the outer div.
        """
        widget_id = self.id()

        label_html = ""
        if self._label:
            label_html = (
                f'<label class="mana-progressbar-label">'
                f'{escape_html(self._label)}'
                f'</label>'
            )

        _, inner_html = self.render_update()

        return (
            f'<div class="mana-progressbar-container">'
            f'{label_html}'
            f'{inner_html}'
            f'</div>'
        )