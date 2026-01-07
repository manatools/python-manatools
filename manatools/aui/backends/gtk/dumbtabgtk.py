# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.gtk contains all GTK backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
'''
'''
GTK4 backend DumbTab (tab bar + single content area)

Implements a simple tab bar using a row of toggle buttons (single selection)
placed above a content area where applications typically attach a ReplacePoint.

This is a YSelectionWidget: it manages items, single selection, and
emits WidgetEvent(Activated) when the active tab changes.
'''
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
import logging
from ...yui_common import *

class YDumbTabGtk(YSelectionWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        self._box = None
        self._tabbar = None
        self._content = None
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)

    def widgetClass(self):
        return "YDumbTab"

    def _create_backend_widget(self):
        try:
            self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            # Gtk4: Use Gtk.StackSwitcher + Gtk.Stack (Notebook-like)
            self._stack = Gtk.Stack()
            try:
                self._stack.set_hexpand(True)
                self._stack.set_vexpand(False)
                # keep stack small; content is below
                self._stack.set_size_request(1, 1)
            except Exception:
                pass
            switcher = Gtk.StackSwitcher()
            try:
                switcher.set_stack(self._stack)
            except Exception:
                pass
            self._tabbar = switcher
            # separate content area below tabs
            self._content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            try:
                self._tabbar.set_hexpand(True)
                self._content.set_hexpand(True)
                self._content.set_vexpand(True)
            except Exception:
                pass
            self._box.append(self._tabbar)
            self._box.append(self._stack)
            self._box.append(self._content)

            # populate tabs/pages from items
            active_idx = -1
            for idx, it in enumerate(self._items):
                # Create an empty page for each tab label
                page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
                name = f"tab-{idx}"
                try:
                    self._stack.add_titled(page, name, it.label())
                except Exception:
                    # Fallback: use add_child then set properties
                    try:
                        self._stack.add_child(page)
                    except Exception:
                        pass
                if it.selected():
                    active_idx = idx
            if active_idx < 0 and len(self._items) > 0:
                active_idx = 0
                try:
                    self._items[0].setSelected(True)
                except Exception:
                    pass
            # set active after building to avoid intermediate signals
            if active_idx >= 0:
                try:
                    self._stack.set_visible_child_name(f"tab-{active_idx}")
                    self._selected_items = [ self._items[active_idx] ]
                except Exception:
                    pass

            # attach pre-existing child content (e.g., ReplacePoint)
            try:
                if self.hasChildren():
                    ch = self.firstChild()
                    if ch is not None:
                        w = ch.get_backend_widget()
                        try:
                            self._content.append(w)
                        except Exception:
                            pass
                        try:
                            self._logger.debug("YDumbTabGtk._create_backend_widget: attached pre-existing child %s", ch.widgetClass())
                        except Exception:
                            pass
            except Exception:
                pass

            self._box.set_sensitive(self._enabled)
            self._backend_widget = self._box
            try:
                self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
            except Exception:
                pass
            # Notify on tab changes
            try:
                self._stack.connect('notify::visible-child-name', self._on_stack_changed)
            except Exception:
                pass
        except Exception:
            try:
                self._logger.exception("YDumbTabGtk _create_backend_widget failed")
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
                self._content.append(w)
                try:
                    self._logger.debug("YDumbTabGtk.addChild: attached %s into content", child.widgetClass())
                except Exception:
                    pass
        except Exception:
            try:
                self._logger.exception("YDumbTabGtk.addChild failed")
            except Exception:
                pass

    def addItem(self, item):
        super().addItem(item)
        try:
            if getattr(self, '_stack', None) is not None:
                page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
                name = f"tab-{len(self._items) - 1}"
                self._stack.add_titled(page, name, item.label())
                if item.selected():
                    try:
                        self._stack.set_visible_child_name(name)
                    except Exception:
                        pass
                self._sync_selection_from_stack()
        except Exception:
            try:
                self._logger.exception("YDumbTabGtk.addItem failed")
            except Exception:
                pass

    def selectItem(self, item, selected=True):
        try:
            if not selected:
                return
            target_idx = None
            for i, it in enumerate(self._items):
                if it is item:
                    target_idx = i
                    break
            if target_idx is None:
                return
            try:
                if getattr(self, '_stack', None) is not None:
                    self._stack.set_visible_child_name(f"tab-{target_idx}")
            except Exception:
                pass
            for it in self._items:
                it.setSelected(False)
            item.setSelected(True)
            self._selected_items = [item]
        except Exception:
            try:
                self._logger.exception("YDumbTabGtk.selectItem failed")
            except Exception:
                pass

    def _on_stack_changed(self, stack, pspec):
        try:
            name = None
            try:
                name = stack.get_visible_child_name()
            except Exception:
                pass
            index = -1
            if name and name.startswith("tab-"):
                try:
                    index = int(name.split("-", 1)[1])
                except Exception:
                    index = -1
            # update model
            if 0 <= index < len(self._items):
                for i, it in enumerate(self._items):
                    try:
                        it.setSelected(i == index)
                    except Exception:
                        pass
                self._selected_items = [ self._items[index] ]
            else:
                self._selected_items = []
            # post event
            if self.notify():
                dlg = self.findDialog()
                if dlg is not None:
                    dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
        except Exception:
            try:
                self._logger.exception("YDumbTabGtk._on_stack_changed failed")
            except Exception:
                pass

    def _sync_selection_from_stack(self):
        try:
            name = self._stack.get_visible_child_name() if getattr(self, '_stack', None) is not None else None
            if name and name.startswith("tab-"):
                i = int(name.split("-", 1)[1])
                if 0 <= i < len(self._items):
                    self._selected_items = [ self._items[i] ]
                    return
            self._selected_items = []
        except Exception:
            self._selected_items = []
