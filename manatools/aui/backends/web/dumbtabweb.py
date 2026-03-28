"""Web backend DumbTab implementation."""
from ...yui_common import YWidget, YItem
from .commonweb import widget_attrs, escape_html

class YDumbTabWeb(YWidget):
    """Tab bar widget with single content area."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tabs = []  # list of YItem
        self._selected_tab = None
    
    def widgetClass(self):
        return "YDumbTab"
    
    def addTab(self, label: str) -> YItem:
        """Add a tab."""
        item = YItem(label)
        item.setIndex(len(self._tabs))
        self._tabs.append(item)
        if self._selected_tab is None:
            self._selected_tab = item
        return item
    
    def addItem(self, item):
        """Add item as tab."""
        if isinstance(item, str):
            return self.addTab(item)
        item.setIndex(len(self._tabs))
        self._tabs.append(item)
        if self._selected_tab is None:
            self._selected_tab = item
        return item
    
    def selectedItem(self):
        return self._selected_tab
    
    def selectItem(self, item, selected=True):
        if selected and item in self._tabs:
            self._selected_tab = item
            self._notify_update()
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        tabs_html = ""
        for tab in self._tabs:
            selected = " selected" if tab == self._selected_tab else ""
            tabs_html += f'<button class="mana-tab{selected}" data-tab-index="{tab.index()}">{escape_html(tab.label())}</button>'
        
        content_html = ""
        for child in self._children:
            content_html += child.render()
        
        attrs = widget_attrs(self.id(), "YDumbTab", self._enabled, self._visible)
        return f'''<div {attrs}>
    <div class="mana-tab-bar">{tabs_html}</div>
    <div class="mana-tab-content">{content_html}</div>
</div>'''
