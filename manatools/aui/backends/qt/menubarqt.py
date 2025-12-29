# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Qt backend: YMenuBar implementation using QMenuBar.
'''
from PySide6 import QtWidgets, QtCore, QtGui
import logging
from ...yui_common import YWidget, YMenuEvent, YMenuItem
from .commonqt import _resolve_icon


class YMenuBarQt(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        self._menus = []  # list of YMenuItem (is_menu=True)
        self._menu_to_qmenu = {}
        self._item_to_qaction = {}

    def widgetClass(self):
        return "YMenuBar"

    def addMenu(self, label: str="", icon_name: str = "", menu: YMenuItem = None) -> YMenuItem:
        """Add a menu by label or by an existing YMenuItem (is_menu=True) to the menubar."""
        m = None
        if menu is not None:
            if not menu.isMenu():
                raise ValueError("Provided YMenuItem is not a menu (is_menu=True)")
            m = menu
        else:
            if not label:
                raise ValueError("Menu label must be provided when no YMenuItem is given")
            m = YMenuItem(label, icon_name, enabled=True, is_menu=True)
        self._menus.append(m)
        if self._backend_widget:
            self._ensure_menu_rendered(m)
        return m

    def addItem(self, menu: YMenuItem, label: str, icon_name: str = "", enabled: bool = True) -> YMenuItem:
        item = menu.addItem(label, icon_name)
        item.setEnabled(enabled)
        if self._backend_widget:
            self._ensure_item_rendered(menu, item)
        return item

    def setItemEnabled(self, item: YMenuItem, on: bool = True):
        item.setEnabled(on)
        act = self._item_to_qaction.get(item)
        if act is not None:
            try:
                act.setEnabled(bool(on))
            except Exception:
                pass

    def setItemVisible(self, item: YMenuItem, visible: bool = True):
        item.setVisible(visible)
        self.rebuildMenus()

    def _path_for_item(self, item: YMenuItem) -> str:
        labels = []
        cur = item
        while cur is not None:
            labels.append(cur.label())
            cur = getattr(cur, "_parent", None)
        return "/".join(reversed(labels))

    def _emit_activation(self, item: YMenuItem):
        try:
            dlg = self.findDialog()
            if dlg and self.notify():
                dlg._post_event(YMenuEvent(item=item, id=self._path_for_item(item)))
        except Exception:
            pass

    def _ensure_menu_rendered(self, menu: YMenuItem):
        # skip invisible top-level menus
        if not menu.visible():
           return

        qmenu = self._menu_to_qmenu.get(menu)
        if qmenu is None:
            qmenu = QtWidgets.QMenu(menu.label(), self._backend_widget)
            # icon via theme
            if menu.iconName():
                try:
                    icon = _resolve_icon(menu.iconName())
                except Exception:
                    icon = QtGui.QIcon.fromTheme(menu.iconName())
                if icon and not icon.isNull():
                    qmenu.setIcon(icon)
            self._backend_widget.addMenu(qmenu)
            self._menu_to_qmenu[menu] = qmenu
            # render children recursively
            self._render_menu_children(menu)
        # ensure the top-level action visibility matches model
        try:
            act = qmenu.menuAction()
            try:
                act.setVisible(bool(menu.visible()))
            except Exception:
                pass
        except Exception:
            pass

    def _render_menu_children(self, menu: YMenuItem):
        """Render all children (items and submenus) of a menu recursively."""
        parent_qmenu = self._menu_to_qmenu.get(menu)
        if parent_qmenu is None:
            return
        for child in list(menu._children):
            try:
                if not child.visible():
                    continue
            except Exception:
                pass
            if child.isMenu():
                sub_qmenu = self._menu_to_qmenu.get(child)
                if sub_qmenu is None:
                    sub_qmenu = parent_qmenu.addMenu(child.label())
                    # icon for submenu
                    if child.iconName():
                        try:
                            icon = _resolve_icon(child.iconName())
                        except Exception:
                            icon = QtGui.QIcon.fromTheme(child.iconName())
                        if icon and not icon.isNull():
                            sub_qmenu.setIcon(icon)
                    self._menu_to_qmenu[child] = sub_qmenu
                    # ensure submenu action visibility
                    try:
                        sa = sub_qmenu.menuAction()
                        try:
                            sa.setVisible(bool(child.visible()))
                        except Exception:
                            pass
                    except Exception:
                        pass
                # recurse into submenu
                self._render_menu_children(child)
            else:
                self._ensure_item_rendered(menu, child)

    def _ensure_item_rendered(self, menu: YMenuItem, item: YMenuItem):
        qmenu = self._menu_to_qmenu.get(menu)
        if qmenu is None:
            self._ensure_menu_rendered(menu)
            qmenu = self._menu_to_qmenu.get(menu)
        if not item.visible():
            return
        if item.isSeparator():
            qmenu.addSeparator()
            return
        act = self._item_to_qaction.get(item)
        if act is None:
            # Resolve icon using common helper (theme or path)
            icon = QtGui.QIcon()
            if item.iconName():
                try:
                    icon = _resolve_icon(item.iconName()) or QtGui.QIcon()
                except Exception:
                    icon = QtGui.QIcon.fromTheme(item.iconName())
            act = QtGui.QAction(icon, item.label(), self._backend_widget)
            act.setEnabled(item.enabled())
            try:
                act.setVisible(bool(item.visible()))
            except Exception:
                pass
            def on_triggered():
                self._emit_activation(item)
            act.triggered.connect(on_triggered)
            qmenu.addAction(act)
            self._item_to_qaction[item] = act
            self._logger.debug("Rendered menu item: %s", self._path_for_item(item))

    def _create_backend_widget(self):
        mb = QtWidgets.QMenuBar()
        self._backend_widget = mb
        try:
            # Prevent vertical stretching: fix height to size hint and set fixed vertical size policy
            h = mb.sizeHint().height()
            if h and h > 0:
                mb.setMinimumHeight(h)
                mb.setMaximumHeight(h)
            sp = mb.sizePolicy()
            sp.setVerticalPolicy(QtWidgets.QSizePolicy.Fixed)
            sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
            mb.setSizePolicy(sp)
        except Exception:
            pass
        # render any menus added before creation
        for m in self._menus:
            self._ensure_menu_rendered(m)
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.setEnabled(bool(enabled))
        except Exception:
            pass

    def rebuildMenus(self):
        """Rebuild all the menus.

        Useful when menu model changes at runtime. 
        
        This action must be performed to reflect any direct changes to
        YMenuItem data (e.g., label, enabled, visible) without passing 
        through the menubar.
        """
        # Rebuild all menus: clear existing QMenu/QAction structures
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    # remove all actions from the menubar
                    for a in list(self._backend_widget.actions()):
                        try:
                            self._backend_widget.removeAction(a)
                        except Exception:
                            self._logger.exception("Failed removing action from menubar")
                            try:
                                a.setVisible(False)
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            pass

        # clear internal mappings so we rebuild from scratch
        try:
            self._menu_to_qmenu.clear()
        except Exception:
            self._menu_to_qmenu = {}
        try:
            self._item_to_qaction.clear()
        except Exception:
            self._item_to_qaction = {}

        # recreate menus as done in _create_backend_widget
        for m in self._menus:
            try:
                self._ensure_menu_rendered(m)
            except Exception:
                self._logger.exception("Failed ensuring menu rendered for '%s'", getattr(m, 'label', lambda: 'unknown')())
        try:
            self._logger.debug("rebuildMenus: recreated menubar <%s>", self.debugLabel())
        except Exception:
            pass

    def deleteMenus(self):
        """Remove all menus/items and their backend QMenu/QAction mappings.

        After clearing model and mappings, call `rebuildMenus()` so the
        backend menubar is emptied.
        """
        try:
            # clear the model (top-level menus)
            try:
                self._menus.clear()
            except Exception:
                self._menus = []

            # remove all actions from the backend widget
            try:
                if getattr(self, "_backend_widget", None) is not None:
                    try:
                        for a in list(self._backend_widget.actions()):
                            try:
                                self._backend_widget.removeAction(a)
                            except Exception:
                                try:
                                    a.setVisible(False)
                                except Exception:
                                    pass
                    except Exception:
                        pass
            except Exception:
                pass

            # clear internal mappings
            try:
                self._menu_to_qmenu.clear()
            except Exception:
                self._menu_to_qmenu = {}
            try:
                self._item_to_qaction.clear()
            except Exception:
                self._item_to_qaction = {}

            # Ensure UI reflects cleared state
            try:
                self.rebuildMenus()
            except Exception:
                pass
        except Exception:
            self._logger.exception("deleteMenus failed")
