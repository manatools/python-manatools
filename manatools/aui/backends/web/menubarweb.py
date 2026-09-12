"""Web backend MenuBar implementation."""
import logging
from ...yui_common import YWidget, YMenuItem, YUIDimension
from .commonweb import widget_attrs, escape_html, format_label_with_shortcut, strip_shortcut


class YMenuBarWeb(YWidget):
    """Menu bar widget - web backend implementation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.web.{self.__class__.__name__}")
        self._menus = []  # list of top-level YMenuItem (is_menu=True)
        try:
            self.setStretchable(YUIDimension.YD_HORIZ, True)
            self.setStretchable(YUIDimension.YD_VERT, False)
        except Exception:
            pass

    def widgetClass(self):
        return "YMenuBar"

    def addMenu(self, label: str = "", icon_name: str = "", menu: YMenuItem = None) -> YMenuItem:
        """Add a top-level menu by label or by an existing YMenuItem (is_menu=True)."""
        if menu is not None:
            if not menu.isMenu():
                raise ValueError("Provided YMenuItem is not a menu (is_menu=True)")
            m = menu
        else:
            if not label:
                raise ValueError("Menu label must be provided when no YMenuItem is given")
            m = YMenuItem(label, icon_name, enabled=True, is_menu=True)
        self._menus.append(m)
        return m

    def addItem(self, menu: YMenuItem, label: str, icon_name: str = "", enabled: bool = True) -> YMenuItem:
        """Add a child item under an existing top-level menu YMenuItem."""
        item = menu.addItem(label, icon_name)
        item.setEnabled(enabled)
        return item

    def setItemEnabled(self, item: YMenuItem, on: bool = True):
        """Enable or disable a menu item."""
        item.setEnabled(on)

    def setItemVisible(self, item: YMenuItem, visible: bool = True):
        """Show or hide a menu item."""
        item.setVisible(visible)

    def deleteMenus(self):
        """Remove all menus and items."""
        try:
            self._menus.clear()
        except Exception:
            self._menus = []

    def rebuildMenus(self):
        """No-op for web backend — render() always reads live model state."""
        pass

    # -------------------------------------------------------------------------
    # Rendering
    # -------------------------------------------------------------------------

    def _render_item(self, item: YMenuItem) -> str:
        """Recursively render a YMenuItem and its children."""
        if item.isSeparator():
            return '<hr class="mana-menu-separator">'

        if item.isMenu() and item.hasChildren():
            children_html = ""
            for child in item.childrenBegin():
                children_html += self._render_item(child)
            visible_cls = "" if item.visible() else " mana-hidden"
            return (
                f'<div class="mana-menu{visible_cls}">'
                f'<span class="mana-menu-label">{format_label_with_shortcut(item.label())}</span>'
                f'<div class="mana-submenu">{children_html}</div>'
                f'</div>'
            )
        else:
            classes = ["mana-menu-item"]
            if not item.enabled():
                classes.append("disabled")
            if not item.visible():
                classes.append("mana-hidden")
            cls = " ".join(classes)
            data_id = f' data-item-id="{id(item)}"'
            # leaf items: strip shortcut marker, escape for safety
            label_html = escape_html(strip_shortcut(item.label()))
            return f'<div class="{cls}"{data_id}>{label_html}</div>'

    def render(self) -> str:
        menus_html = ""
        for menu in self._menus:
            if not menu.visible():
                continue
            menus_html += self._render_item(menu)

        attrs = widget_attrs(self.id(), "YMenuBar", self._enabled, self._visible)
        return f'<nav {attrs}>{menus_html}</nav>'