# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Qt backend: YMenuBar implementation using QMenuBar.
'''
from PySide6 import QtWidgets, QtCore, QtGui
import logging
from ...yui_common import YWidget, YMenuEvent, YMenuItem


class YMenuBarQt(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        self._menus = []  # list of YMenuItem (is_menu=True)
        self._menu_to_qmenu = {}
        self._item_to_qaction = {}

    def widgetClass(self):
        return "YMenuBar"

    def addMenu(self, label: str, icon_name: str = "") -> YMenuItem:
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
        qmenu = self._menu_to_qmenu.get(menu)
        if qmenu is None:
            qmenu = QtWidgets.QMenu(menu.label(), self._backend_widget)
            # icon via theme
            if menu.iconName():
                icon = QtGui.QIcon.fromTheme(menu.iconName())
                if not icon.isNull():
                    qmenu.setIcon(icon)
            self._backend_widget.addMenu(qmenu)
            self._menu_to_qmenu[menu] = qmenu
            # render children if any
            for child in list(menu._children):
                if child.isMenu():
                    sub = qmenu.addMenu(child.label())
                    if child.iconName():
                        icon = QtGui.QIcon.fromTheme(child.iconName())
                        if not icon.isNull():
                            sub.setIcon(icon)
                    self._menu_to_qmenu[child] = sub
                else:
                    self._ensure_item_rendered(menu, child)

    def _ensure_item_rendered(self, menu: YMenuItem, item: YMenuItem):
        qmenu = self._menu_to_qmenu.get(menu)
        if qmenu is None:
            self._ensure_menu_rendered(menu)
            qmenu = self._menu_to_qmenu.get(menu)
        if item.label() == "-":
            qmenu.addSeparator()
            return
        act = self._item_to_qaction.get(item)
        if act is None:
            #TODO use _resolve_icon from commonqt.py
            icon = QtGui.QIcon.fromTheme(item.iconName()) if item.iconName() else QtGui.QIcon()
            act = QtGui.QAction(icon, item.label(), self._backend_widget)
            act.setEnabled(item.enabled())
            def on_triggered():
                self._emit_activation(item)
            act.triggered.connect(on_triggered)
            qmenu.addAction(act)
            self._item_to_qaction[item] = act

    def _create_backend_widget(self):
        mb = QtWidgets.QMenuBar()
        self._backend_widget = mb
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