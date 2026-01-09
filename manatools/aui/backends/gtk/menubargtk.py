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
import os
from ...yui_common import YWidget, YMenuEvent, YMenuItem, YUIDimension
from .commongtk import _resolve_gicon, _resolve_icon


class YMenuBarGtk(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        self._menus = []  # top-level YMenuItem menus
        self._menu_to_model = {}
        # For MenuButton+Popover approach
        self._menu_to_button = {}
        self._item_to_row = {}
        self._row_to_item = {}
        self._row_to_popover = {}
        self._pending_rebuild = False
        # Default stretch: horizontal True, vertical False
        try:
            self.setStretchable(YUIDimension.YD_HORIZ, True)
            self.setStretchable(YUIDimension.YD_VERT, False)
        except Exception:
            pass

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
        # Update rendered row or button sensitivity if present
        try:
            row = self._item_to_row.get(item)
            if row is not None:
                try:
                    row.set_sensitive(bool(on))
                except Exception:
                    pass
                return
            pair = self._menu_to_button.get(item)
            if pair is not None:
                try:
                    btn, _ = pair
                    btn.set_sensitive(bool(on))
                except Exception:
                    pass
        except Exception:
            self._logger.exception("Error updating enabled state for menu item '%s'", getattr(item, 'label', lambda: 'unknown')())

    def setItemVisible(self, item: YMenuItem, visible: bool = True):
        item.setVisible(visible)
        # Defer rebuild to idle to avoid clearing widgets during signal emission
        self._queue_rebuild()

    def _queue_rebuild(self):
        try:
            if self._pending_rebuild:
                return
            self._pending_rebuild = True
            def do_rebuild():
                try:
                    self.rebuildMenus()
                except Exception:
                    self._logger.exception("Deferred rebuildMenus failed")
                finally:
                    self._pending_rebuild = False
                return False  # remove idle source
            try:
                GLib.idle_add(do_rebuild, priority=GLib.PRIORITY_DEFAULT_IDLE)
            except Exception:
                # Fallback: rebuild synchronously if idle_add not available
                try:
                    self.rebuildMenus()
                finally:
                    self._pending_rebuild = False
        except Exception:
            self._logger.exception("_queue_rebuild failed")

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
        # For backwards compatibility call-through to button renderer
        try:
            self._ensure_menu_rendered_button(menu)
        except Exception:
            self._logger.exception("Failed to ensure menu rendered for '%s'", menu.label())

    def _action_name_for_item(self, item: YMenuItem) -> str:
        # derive action id from path, sanitized
        path = self._path_for_item(item)
        return path.replace('/', '_').replace(' ', '_').lower()

    def _populate_menu_model(self, model: Gio.Menu, menu: YMenuItem):
        # This implementation builds per-menu Gtk.Popover/ListBox widgets instead of a Gio.Menu model.
        # Population is handled by `_render_menu_children` when menus are rendered.
        return

    def _ensure_menu_rendered_button(self, menu: YMenuItem):
        # Create a MenuButton with a Popover containing a ListBox for `menu` children.
        if menu in self._menu_to_button:
            return
        hb = self._backend_widget
        if hb is None:
            return
        btn = Gtk.MenuButton()
        try:
            btn.set_label(menu.label())
            btn.set_has_frame(False)
        except Exception:
            pass

        # optional icon on the button
        if menu.iconName():
            try:
                img = _resolve_icon(menu.iconName())
                if img is not None:
                    try:
                        btn.set_icon(img.get_paintable())
                    except Exception:
                        # Some Gtk versions may not support set_icon; try set_child with a box
                        try:
                            hb_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                            hb_box.append(img)
                            btn.set_child(hb_box)
                        except Exception:
                            self._logger.exception("Failed to set icon on MenuButton for '%s'", menu.label())
            except Exception:
                self._logger.exception("Error resolving icon for MenuButton '%s'", menu.label())

        pop = Gtk.Popover()
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.connect("row-activated", self._on_row_activated)
        pop.set_child(listbox)
        btn.set_popover(pop)
        # ensure button doesn't expand vertically
        try:
            btn.set_vexpand(False)
            btn.set_hexpand(False)
        except Exception:
            pass
        try:
            hb.append(btn)
        except Exception:
            try:
                hb.add(btn)
            except Exception:
                pass

        self._menu_to_button[menu] = (btn, listbox)
        # populate listbox rows
        self._render_menu_children(menu)
        # reflect initial visibility
        try:
            btn.set_visible(bool(menu.visible()))
        except Exception:
            pass

    def _render_menu_children(self, menu: YMenuItem):
        pair = self._menu_to_button.get(menu)
        if not pair:
            return
        btn, listbox = pair
        # clear existing rows reliably on GTK4
        try:
            self.__clear_widget(listbox)
        except Exception:
            pass

        for child in list(menu._children):
            # skip invisible children
            try:
                if not child.visible():
                    continue
            except Exception:
                pass
            if child.isMenu():
                # submenu: create a nested MenuButton inside the row
                sub_btn = Gtk.MenuButton()
                try:
                    sub_btn.set_label(child.label())
                    sub_btn.set_has_frame(False)
                except Exception:
                    pass
                sub_pop = Gtk.Popover()
                sub_lb = Gtk.ListBox()
                sub_lb.set_selection_mode(Gtk.SelectionMode.NONE)
                sub_lb.connect("row-activated", self._on_row_activated)
                sub_pop.set_child(sub_lb)
                sub_btn.set_popover(sub_pop)
                # optional icon
                if child.iconName():
                    try:
                        img = _resolve_icon(child.iconName())
                        if img is not None:
                            try:
                                sub_btn.set_icon(img.get_paintable())
                            except Exception:
                                try:
                                    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                                    box.append(img)
                                    sub_btn.set_child(box)
                                except Exception:
                                    self._logger.exception("Failed to set icon on submenu button '%s'", child.label())
                    except Exception:
                        self._logger.exception("Error resolving icon for submenu '%s'", child.label())

                row = Gtk.ListBoxRow()
                row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                row_box.append(sub_btn)
                row.set_child(row_box)
                row.set_sensitive(child.enabled())
                listbox.append(row)
                # store mapping and recurse
                self._menu_to_button[child] = (sub_btn, sub_lb)
                # map rows in submenu to its popover so we can close it on activation
                try:
                    self._row_to_popover[row] = sub_btn.get_popover()
                except Exception:
                    pass
                self._render_menu_children(child)
            else:
                # skip invisible children
                try:
                    if not child.visible():
                        continue
                except Exception:
                    pass
                if child.isSeparator():
                    sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
                    listbox.append(sep)
                    continue
                row = Gtk.ListBoxRow()
                row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                # optional icon
                if child.iconName():
                    try:
                        img = _resolve_icon(child.iconName())
                        if img is not None:
                            row_box.append(img)
                    except Exception:
                        self._logger.exception("Failed to resolve icon for menu item '%s'", child.label())
                lbl = Gtk.Label(label=child.label())
                lbl.set_xalign(0.0)
                row_box.append(lbl)
                row.set_child(row_box)
                row.set_sensitive(child.enabled())
                listbox.append(row)
                self._item_to_row[child] = row
                self._row_to_item[row] = child
                # remember the popover that contains this row (top-level menu)
                try:
                    self._row_to_popover[row] = btn.get_popover()
                except Exception:
                    pass

    def _create_backend_widget(self):
        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        # Expansion based on current stretchable flags: default hexpand True, vexpand False
        try:
            try:
                v_stretch = bool(self.stretchable(YUIDimension.YD_VERT))
            except Exception:
                v_stretch = False
            try:
                h_stretch = bool(self.stretchable(YUIDimension.YD_HORIZ))
            except Exception:
                h_stretch = True
            hb.set_vexpand(v_stretch)
            hb.set_hexpand(h_stretch)
        except Exception:
            pass
        self._backend_widget = hb
        # render any visible menus added before creation
        for m in self._menus:
            try:
                if not m.visible():
                    continue
                self._ensure_menu_rendered_button(m)
            except Exception:
                self._logger.exception("Failed to render menu '%s'", m.label())

    def _rebuild_root_model(self):
        # Re-render all menus and their popovers to reflect model changes
        try:
            for m in list(self._menus):
                try:
                    try:
                        if not m.visible():
                            continue
                    except Exception:
                        pass
                    self._ensure_menu_rendered_button(m)
                    self._render_menu_children(m)
                except Exception:
                    self._logger.exception("Failed rebuilding menu '%s'", m.label())
        except Exception:
            self._logger.exception("Unexpected error in _rebuild_root_model")

    def __clear_widget(self, widget: Gtk.Widget):
        """Remove all children from a GTK4 widget.

        Recursively unparents/removes children to help rebuild container
        widgets safely.
        """
        if not widget:
            return
        
        child = widget.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.__clear_widget(child) 

            if hasattr(widget, 'remove'):
                widget.remove(child)
            #elif hasattr(child, 'unparent'):
            #    child.unparent()
 
            child = next_child

    def rebuildMenus(self):
        """Rebuild all the menus.

        Useful when the menu model changes at runtime.

        This action must be performed to reflect any direct changes to
        `YMenuItem` data (e.g., label, enabled, visible) without going
        through higher-level menubar helpers.
        """
        try:
            hb = self._backend_widget
            # proactively disconnect signals and close popovers before clearing children
            try:
                for _m, pair in list(self._menu_to_button.items()):
                    try:
                        btn, listbox = pair
                        # disconnect row-activated if available
                        try:
                            if hasattr(listbox, 'disconnect_by_func'):
                                listbox.disconnect_by_func(self._on_row_activated)
                        except Exception:
                            pass
                        # close/detach popover
                        try:
                            pop = btn.get_popover()
                            if pop is not None:
                                try:
                                    pop.popdown()
                                except Exception:
                                    try:
                                        pop.set_visible(False)
                                    except Exception:
                                        try:
                                            pop.hide()
                                        except Exception:
                                            pass
                                try:
                                    pop.set_child(None)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    except Exception:
                        pass
            except Exception:
                pass
            self.__clear_widget(hb)            

            # clear mappings
            try:
                self._menu_to_button.clear()
            except Exception:
                self._menu_to_button = {}
            try:
                self._item_to_row.clear()
            except Exception:
                self._item_to_row = {}
            try:
                self._row_to_item.clear()
            except Exception:
                self._row_to_item = {}
            try:
                self._row_to_popover.clear()
            except Exception:
                self._row_to_popover = {}

            # recreate top-level buttons like in _create_backend_widget
            for m in self._menus:
                try:
                    self._ensure_menu_rendered_button(m)
                    # set button visibility according to model
                    try:
                        pair = self._menu_to_button.get(m)
                        if pair is not None:
                            try:
                                btn, _ = pair
                                btn.set_visible(bool(m.visible()))
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    self._logger.exception("Failed to ensure menu rendered for '%s'", m.label())

        except Exception:
            self._logger.exception("rebuildMenus failed")

    def deleteMenus(self):
        """Remove all top-level menus and their backend widgets/mappings.

        Clears the `self._menus` model list and removes any created
        MenuButton widgets from the backend container, then invokes
        `rebuildMenus()` so the UI is updated.
        """
        try:
            # clear model
            try:
                self._menus.clear()
            except Exception:
                self._menus = []

            # remove buttons from container, disconnect signals and clear listboxes
            try:
                hb = self._backend_widget
                for m, pair in list(self._menu_to_button.items()):
                    btn, listbox = pair
                    # disconnect row-activated if available
                    try:
                        if hasattr(listbox, 'disconnect_by_func'):
                            listbox.disconnect_by_func(self._on_row_activated)
                    except Exception:
                        pass
                    # close/detach popover
                    try:
                        pop = btn.get_popover()
                        if pop is not None:
                            try:
                                pop.popdown()
                            except Exception:
                                try:
                                    pop.set_visible(False)
                                except Exception:
                                    try:
                                        pop.hide()
                                    except Exception:
                                        pass
                            try:
                                pop.set_child(None)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    self.__clear_widget(hb)
            except Exception:
                pass

            # clear mappings
            try:
                self._menu_to_button.clear()
            except Exception:
                self._menu_to_button = {}
            try:
                self._item_to_row.clear()
            except Exception:
                self._item_to_row = {}
            try:
                self._row_to_item.clear()
            except Exception:
                self._row_to_item = {}
            try:
                self._row_to_popover.clear()
            except Exception:
                self._row_to_popover = {}

            # reflect empty state
            try:
                self.rebuildMenus()
            except Exception:
                pass
        except Exception:
            self._logger.exception("deleteMenus failed")

    

    def _set_backend_enabled(self, enabled):
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.set_sensitive(bool(enabled))
        except Exception:
            pass

    # ListBox activation handled by `_on_row_activated`

    def _on_row_activated(self, listbox: Gtk.ListBox, row: Gtk.ListBoxRow):
        try:
            item = self._row_to_item.get(row)
            if item and item.enabled():
                self._emit_activation(item)
                # Close any popovers related to the menubar to mimic standard menu behavior
                try:
                    for btn, _lb in list(self._menu_to_button.values()):
                        try:
                            pop = None
                            try:
                                pop = btn.get_popover()
                            except Exception:
                                pop = None
                            if pop is None:
                                continue
                            # Try popdown(), else hide/set_visible(False)
                            try:
                                pop.popdown()
                            except Exception:
                                try:
                                    pop.set_visible(False)
                                except Exception:
                                    try:
                                        pop.hide()
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                except Exception:
                    self._logger.exception("Error closing popovers after activation")
        except Exception:
            self._logger.exception("Error handling row activation")
