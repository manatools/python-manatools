# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Qt backend DumbTab (tab bar + single content area)

Implements a simple tab bar using QTabBar and exposes a single child
content area where applications typically attach a YReplacePoint.

This is a YSelectionWidget: it manages items, single selection, and
emits WidgetEvent(Activated) when the active tab changes.
'''
from PySide6 import QtWidgets, QtCore
import logging
from ...yui_common import *

class YDumbTabQt(YSelectionWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        self._container = None
        self._tabbar = None
        self._content = None  # placeholder QWidget for the single child
        # DumbTab is horizontally stretchable and minimally vertically
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)

    def widgetClass(self):
        return "YDumbTab"

    def _create_backend_widget(self):
        try:
            container = QtWidgets.QWidget()
            v = QtWidgets.QVBoxLayout(container)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(5)

            tabbar = QtWidgets.QTabBar()
            tabbar.setExpanding(False)
            tabbar.setMovable(False)
            tabbar.setTabsClosable(False)

            content = QtWidgets.QWidget()
            content.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            content_layout = QtWidgets.QVBoxLayout(content)
            content_layout.setContentsMargins(0, 0, 0, 0)

            v.addWidget(tabbar)
            v.addWidget(content, 1)

            tabbar.currentChanged.connect(self._on_tab_changed)

            # populate from existing items respecting selected flags
            selected_idx = -1
            for idx, it in enumerate(self._items):
                try:
                    tabbar.addTab(it.label())
                    if it.selected():
                        selected_idx = idx
                except Exception:
                    tabbar.addTab(str(it))
            if selected_idx < 0 and len(self._items) > 0:
                selected_idx = 0
                try:
                    self._items[0].setSelected(True)
                except Exception:
                    pass
            if selected_idx >= 0:
                try:
                    tabbar.setCurrentIndex(selected_idx)
                except Exception:
                    pass
                self._selected_items = [ self._items[selected_idx] ]

            container.setEnabled(bool(self._enabled))

            self._backend_widget = container
            self._container = container
            self._tabbar = tabbar
            self._content = content
            # If a child was added before backend creation (common in tests), attach it now
            try:
                if self.hasChildren():
                    ch = self.firstChild()
                    if ch is not None:
                        w = ch.get_backend_widget()
                        lay = self._content.layout() or QtWidgets.QVBoxLayout(self._content)
                        self._content.setLayout(lay)
                        try:
                            w.setParent(self._content)
                        except Exception:
                            pass
                        lay.addWidget(w)
                        try:
                            w.show()
                            w.updateGeometry()
                        except Exception:
                            pass
                        try:
                            self._logger.debug("YDumbTabQt._create_backend_widget: attached pre-existing child %s", ch.widgetClass())
                        except Exception:
                            pass
            except Exception:
                pass
            try:
                self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
            except Exception:
                pass
        except Exception:
            try:
                self._logger.exception("YDumbTabQt _create_backend_widget failed")
            except Exception:
                pass

    def addChild(self, child):
        # Accept only a single child; attach its backend into content area
        if self.hasChildren():
            raise YUIInvalidWidgetException("YDumbTab can only have one child")
        super().addChild(child)
        try:
            if self._content is not None:
                w = child.get_backend_widget()
                lay = self._content.layout() or QtWidgets.QVBoxLayout(self._content)
                self._content.setLayout(lay)
                try:
                    # Ensure proper parenting before adding to layout to avoid invisibility
                    w.setParent(self._content)
                except Exception:
                    pass
                lay.addWidget(w)
                try:
                    w.show()
                    w.updateGeometry()
                except Exception:
                    pass
                try:
                    self._logger.debug("YDumbTabQt.addChild: attached %s into content", child.widgetClass())
                except Exception:
                    pass
        except Exception:
            try:
                self._logger.exception("YDumbTabQt.addChild failed")
            except Exception:
                pass

    def addItem(self, item):
        super().addItem(item)
        try:
            if self._tabbar is not None:
                idx = self._tabbar.addTab(item.label())
                if item.selected():
                    try:
                        self._tabbar.setCurrentIndex(idx)
                    except Exception:
                        pass
                # sync internal selection list
                self._sync_selection_from_tabbar()
        except Exception:
            try:
                self._logger.exception("YDumbTabQt.addItem failed")
            except Exception:
                pass

    def selectItem(self, item, selected=True):
        # single selection: set current tab to item's index
        try:
            if not selected:
                return
            idx = None
            for i, it in enumerate(self._items):
                if it is item:
                    idx = i
                    break
            if idx is None:
                return
            if self._tabbar is not None:
                self._tabbar.setCurrentIndex(idx)
            # sync model
            for it in self._items:
                it.setSelected(False)
            item.setSelected(True)
            self._selected_items = [item]
        except Exception:
            try:
                self._logger.exception("YDumbTabQt.selectItem failed")
            except Exception:
                pass

    def _on_tab_changed(self, index):
        try:
            # Update model selection
            for i, it in enumerate(self._items):
                try:
                    it.setSelected(i == index)
                except Exception:
                    pass
            self._selected_items = [ self._items[index] ] if 0 <= index < len(self._items) else []
            # Post activation event
            if self.notify():
                dlg = self.findDialog()
                if dlg is not None:
                    dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
        except Exception:
            try:
                self._logger.exception("YDumbTabQt._on_tab_changed failed")
            except Exception:
                pass

    def _sync_selection_from_tabbar(self):
        try:
            idx = self._tabbar.currentIndex() if self._tabbar is not None else -1
            self._selected_items = [ self._items[idx] ] if 0 <= idx < len(self._items) else []
        except Exception:
            self._selected_items = []
