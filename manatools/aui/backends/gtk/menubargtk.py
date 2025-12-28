# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
GTK backend: YMenuBar implementation using a horizontal box of MenuButtons with Popovers.
GTK4 lacks traditional Gtk.MenuBar; this simulates a menubar.
'''
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Gio, GLib
import logging
from ...yui_common import YWidget, YMenuEvent, YMenuItem
from .commongtk import _resolve_gicon, _resolve_icon


class YMenuBarGtk(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        self._menus = []  # top-level YMenuItem menus
        self._menu_to_model = {}
        self._item_to_action = {}
        self._action_group = Gio.SimpleActionGroup()

    def widgetClass(self):
        return "YMenuBar"

    def addMenu(self, label: str, icon_name: str = "") -> YMenuItem:
        m = YMenuItem(label, icon_name, enabled=True, is_menu=True)
        self._menus.append(m)
        if self._backend_widget:
            self._ensure_menu_rendered(m)
            self._rebuild_root_model()
        return m

    def addItem(self, menu: YMenuItem, label: str, icon_name: str = "", enabled: bool = True) -> YMenuItem:
        item = menu.addItem(label, icon_name)
        item.setEnabled(enabled)
        if self._backend_widget:
            # update model for this menu and rebuild root
            self._ensure_menu_rendered(menu)
            self._rebuild_root_model()
        return item

    def setItemEnabled(self, item: YMenuItem, on: bool = True):
        item.setEnabled(on)
        act = self._item_to_action.get(item)
        if act is not None:
            try:
                act.set_enabled(bool(on))
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
        # Build Gio.Menu model for this menu
        model = Gio.Menu()
        self._menu_to_model[menu] = model
        self._populate_menu_model(model, menu)

    def _action_name_for_item(self, item: YMenuItem) -> str:
        # derive action id from path, sanitized
        path = self._path_for_item(item)
        return path.replace('/', '_').replace(' ', '_').lower()

    def _populate_menu_model(self, model: Gio.Menu, menu: YMenuItem):
        for child in list(menu._children):
            if child.isMenu():
                sub_model = Gio.Menu()
                self._populate_menu_model(sub_model, child)
                model.append_submenu(child.label(), sub_model)
            else:
                if child.label() == "-":
                    # separator
                    model.append_section(None, Gio.Menu())
                    continue
                item = Gio.MenuItem.new(child.label(), None)
                image = _resolve_icon(child.iconName()) if child.iconName() else None
                if image is None and child.iconName():
                    self._logger.error("Failed to resolve icon for menu item <%s> <%s>", child.label(), child.iconName())
                gicon = image.get_gicon() if image else None
                if gicon is not None:
                    try:
                        item.set_icon(gicon)
                    except Exception:
                        self._logger.error("Failed to set icon for menu item <%s>", child.label(), exc_info=True)
                        pass
                elif child.iconName():
                    self._logger.error("No icon for menu item <%s> <%s>", child.label(), child.iconName())
                act_name = self._action_name_for_item(child)
                action = Gio.SimpleAction.new(act_name, None)
                # honor initial enabled state from the YMenuItem model
                try:
                    action.set_enabled(bool(child.enabled()))
                except Exception:
                    pass
                def on_activate(_action, _param=None, _child=child):
                    if not _child.enabled():
                        return
                    self._emit_activation(_child)
                action.connect("activate", on_activate)
                try:
                    self._action_group.add_action(action)
                except Exception:
                    pass
                self._item_to_action[child] = action
                try:
                    item.set_attribute_value("action", GLib.Variant.new_string(f"menubar.{act_name}"))
                    # also set enabled attribute to guide rendering
                    try:
                        item.set_attribute_value("enabled", GLib.Variant.new_boolean(bool(child.enabled())))
                    except Exception:
                        pass
                except Exception:
                    pass
                model.append_item(item)

    # no per-item rendering in PopoverMenuBar approach

    def _create_backend_widget(self):
        # Combine all top-level menus into a single model
        root = Gio.Menu()
        for m in self._menus:
            self._ensure_menu_rendered(m)
            model = self._menu_to_model.get(m)
            if model is not None:
                root.append_submenu(m.label(), model)
        mb = Gtk.PopoverMenuBar.new_from_model(root)
        try:
            mb.insert_action_group("menubar", self._action_group)
        except Exception:
            pass
        # Limit vertical expansion
        #try:
        #    mb.set_vexpand(False)
        #    mb.set_hexpand(True)
        #except Exception:
        #    pass
        self._backend_widget = mb

    def _rebuild_root_model(self):
        try:
            mb = self._backend_widget
            if mb is None:
                return
            # Reset actions to keep state in sync
            self._action_group = Gio.SimpleActionGroup()
            self._item_to_action.clear()
            root = Gio.Menu()
            for m in self._menus:
                # Ensure individual menu model exists and is populated
                self._ensure_menu_rendered(m)
                model = self._menu_to_model.get(m)
                if model is not None:
                    # refresh model contents
                    refreshed = Gio.Menu()
                    self._populate_menu_model(refreshed, m)
                    self._menu_to_model[m] = refreshed
                    root.append_submenu(m.label(), refreshed)
            try:
                mb.set_menu_model(root)
            except Exception:
                # Fallback: recreate component if setter not available
                pass
            try:
                mb.insert_action_group("menubar", self._action_group)
            except Exception:
                pass
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.set_sensitive(bool(enabled))
        except Exception:
            pass

    # No ListBox activation in PopoverMenuBar implementation
