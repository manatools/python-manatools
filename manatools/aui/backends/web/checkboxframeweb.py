"""Web backend CheckBoxFrame implementation."""
from ...yui_common import (YSingleChildContainerWidget, YProperty, YPropertySet,
                           YPropertyType)
from .commonweb import widget_attrs, escape_html, format_label_with_shortcut

class YCheckBoxFrameWeb(YSingleChildContainerWidget):
    """Frame with a checkbox in the legend that enables/disables content."""
    def __init__(self, parent=None, label: str = "", checked: bool = False):
        # Attributes first: addChild() on the parent may render us immediately.
        self._label = label
        self._checked = bool(checked)
        self._auto_enable = True
        self._invert_auto = False
        self._show_content = True
        super().__init__(parent)

    def widgetClass(self):
        return "YCheckBoxFrame"

    def label(self) -> str:
        return self._label

    def setLabel(self, label: str):
        self._label = label
        self._notify_update()

    def value(self) -> bool:
        return self._checked

    def setValue(self, isChecked: bool):
        isChecked = bool(isChecked)
        if isChecked == self._checked:
            return
        self._checked = isChecked
        self._notify_update()

    def autoEnable(self) -> bool:
        return self._auto_enable

    def setAutoEnable(self, autoEnable: bool):
        self._auto_enable = bool(autoEnable)
        self._notify_update()

    def invertAutoEnable(self) -> bool:
        return self._invert_auto

    def setInvertAutoEnable(self, invert: bool):
        self._invert_auto = bool(invert)
        self._notify_update()

    def showContent(self, visible: bool = True):
        """Show or hide the content area without touching the checkbox."""
        self._show_content = bool(visible)
        self._notify_update()

    def addChild(self, child):
        super().addChild(child)
        self._notify_update()

    def setProperty(self, propertyName: str, val) -> bool:
        if propertyName == "label":
            self.setLabel(str(val))
            return True
        if propertyName in ("value", "checked"):
            self.setValue(bool(val))
            return True
        return False

    def getProperty(self, propertyName: str):
        if propertyName == "label":
            return self._label
        if propertyName in ("value", "checked"):
            return self._checked
        return None

    def propertySet(self):
        props = YPropertySet()
        props.add(YProperty("label", YPropertyType.YStringProperty))
        props.add(YProperty("value", YPropertyType.YBoolProperty))
        return props

    def _content_enabled(self) -> bool:
        """Effective enablement of the content area: the checkbox state when
        autoEnable is on (inverted on request), otherwise always on."""
        if not self._enabled:
            return False
        if not self._auto_enable:
            return True
        return (not self._checked) if self._invert_auto else self._checked

    def _set_backend_enabled(self, enabled: bool):
        child = self.child()
        if child is not None:
            child._set_backend_enabled(enabled and child._enabled)
        self._notify_update()

    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)

    def render(self) -> str:
        attrs = widget_attrs(self.id(), "YCheckBoxFrame", self._enabled, self._visible)

        checked_attr = " checked" if self._checked else ""
        label_html = format_label_with_shortcut(self._label)

        legend = f'''<legend class="mana-checkboxframe-legend">
            <input type="checkbox" class="mana-checkboxframe-toggle"{checked_attr}>
            <span>{label_html}</span>
        </legend>'''

        content = ""
        if self.child():
            content = self.child().render()

        disabled_class = "" if self._content_enabled() else " mana-disabled"
        hidden_style = "" if self._show_content else ' style="display: none"'
        return (f'<fieldset {attrs}>{legend}'
                f'<div class="mana-checkboxframe-content{disabled_class}"{hidden_style}>'
                f'{content}</div></fieldset>')
