# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.gtk contains all GTK backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
'''

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, GObject, GdkPixbuf, GLib, Gio
import cairo
import threading
import os
import logging
from ...yui_common import *


__all__ = ["_resolve_icon", "_resolve_gicon", "_convert_mnemonic_to_gtk",
           "_install_context_menu_triggers", "_listbox_context_row", "_open_context_menu"]


def _resolve_icon(icon_name, size=16):
        """Return a `Gtk.Image` for the given icon_name or None.

        Resolution policy:
        - If `icon_name` looks like a filesystem path (absolute or contains path
        separator) or the file exists, load from file. If no extension, also
        try the same path with `.png` appended.
        - Otherwise, strip any extension and try to load from the system
        icon theme. If that fails, try creating an image from the original
        name (some engines accept full names).
        """        
        if not icon_name:
            return None
        
        # Helper function to load from file
        def load_from_file(filename):
            if os.path.exists(filename):
                try:
                    # Try as a file path
                    picture = Gtk.Picture.new_for_filename(filename)
                    if picture.get_paintable():
                        image = Gtk.Image.new_from_paintable(picture.get_paintable())
                        if image.get_paintable():
                            return image
                except Exception:
                    pass
                
                # Alternative: try GdkPixbuf
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
                    if pixbuf:
                        return Gtk.Image.new_from_pixbuf(pixbuf)
                except Exception:
                    pass
            return None
        
        # Step 1: Try as file path
        try:
            if (os.path.isabs(icon_name) or 
                os.path.sep in icon_name or 
                os.path.exists(icon_name)):
                
                result = load_from_file(icon_name)
                if result:
                    return result
                
                # If no extension, try with .png
                base, ext = os.path.splitext(icon_name)
                if not ext:
                    result = load_from_file(icon_name + '.png')
                    if result:
                        return result
        except Exception:
            pass
        
        # Step 2: Try icon theme
        try:
            # Strip extension for icon name
            base_name = os.path.splitext(icon_name)[0] if '.' in icon_name else icon_name
            
            # Get default display and theme
            display = Gdk.Display.get_default()
            if display:
                theme = Gtk.IconTheme.get_for_display(display)
                
                # Try to lookup the icon
                paint = theme.lookup_icon(
                    base_name,
                    fallbacks=None,
                    size=size,
                    scale=1,
                    direction=Gtk.TextDirection.LTR,
                    flags=Gtk.IconLookupFlags.FORCE_REGULAR
                )
                
                if paint:
                    return Gtk.Image.new_from_paintable(paint)
            
            # Fallback: simple icon name creation
            image = Gtk.Image.new_from_icon_name(base_name)
            if image.get_icon_name():  # Check if icon was actually set
                return image
                
        except Exception:
            pass
        
        # Step 3: Final attempt with original name
        try:
            image = Gtk.Image.new_from_icon_name(icon_name)
            if image.get_icon_name():
                return image
        except Exception:
            pass
        
        return None


def _resolve_gicon(icon_spec):
        """Resolve icon specification to a Gio.Icon.

        Supports theme icon names (Gio.ThemedIcon) and absolute file paths
        (Gio.FileIcon). Returns None if it cannot be resolved.
        """
        if not icon_spec:
            return None
        try:
            # absolute file path
            if os.path.isabs(icon_spec) and os.path.exists(icon_spec):
                try:
                    gfile = Gio.File.new_for_path(icon_spec)
                    return Gio.FileIcon.new(gfile)
                except Exception:
                    pass
            # theme icon
            base_name = os.path.splitext(icon_spec)[0] if '.' in icon_spec else icon_spec
            try:
                return Gio.ThemedIcon.new(base_name)
            except Exception:
                pass
        except Exception:
            pass
        return None


def _convert_mnemonic_to_gtk(label: str) -> str:
    """Convert a Qt-style mnemonic in a label to GTK format.

    - Qt: uses '&' before a character to mark the mnemonic (e.g., "&Quit").
           A literal ampersand is written as "&&".
    - GTK: uses '_' before the mnemonic character (e.g., "_Quit").

    If no mnemonic marker ('&' not present), the string is returned unchanged.
    Literal "&&" sequences are converted to a single '&'. Only the first
    single '&' is converted to a mnemonic; subsequent single '&' are dropped.

    This function does not attempt to escape underscores; GTK treats '_' as
    mnemonic when present, but the input is expected to be Qt-style.
    """
    if label is None:
        return label
    s = str(label)
    if '&' not in s:
        return s

    out = []
    i = 0
    mnemonic_done = False
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == '&':
            # Handle literal ampersand
            if i + 1 < n and s[i + 1] == '&':
                out.append('&')
                i += 2
                continue
            # Single '&' indicates mnemonic; convert the first occurrence
            if not mnemonic_done:
                # Insert '_' before the next character (if any)
                if i + 1 < n:
                    out.append('_')
                mnemonic_done = True
            # Skip this '&' (do not add to output)
            i += 1
            continue
        else:
            out.append(ch)
            i += 1
    return ''.join(out)


def _point_rect(x, y, width=1, height=1):
    rect = Gdk.Rectangle()
    rect.x, rect.y, rect.width, rect.height = int(x), int(y), int(width), int(height)
    return rect


def _widget_rect(child, ancestor):
    """Return the bounds of child in ancestor coordinates, or None."""
    try:
        ok, bounds = child.compute_bounds(ancestor)
    except Exception:
        return None
    if not ok:
        return None
    return _point_rect(bounds.get_x(), bounds.get_y(),
                       max(1, bounds.get_width()), max(1, bounds.get_height()))


def _install_context_menu_triggers(owner, widget, row_at, focus_row):
    """Post ContextMenuActivated on right-click, long-press, Shift+F10 or Menu.

    row_at(x, y) and focus_row() locate a row in widget and return None or a
    tuple (is_selected, select_only, rect) with rect a Gdk.Rectangle in widget
    coordinates. Nothing happens unless owner.notifyContextMenu() is set, so
    widgets need no setter override.
    """
    logger = logging.getLogger("manatools.aui.gtk.common")

    def request(hit, anchor):
        # Right-click on an unselected row selects only that row first, so the
        # handler can rely on selectedItem(); inside a selection keep it.
        if hit is not None and not hit[0]:
            hit[1]()
        dlg = owner.findDialog()
        if dlg is None:
            return
        dlg._context_menu_source = owner
        dlg._context_menu_anchor = (widget, anchor)
        dlg._post_event(YWidgetEvent(owner, YEventReason.ContextMenuActivated))

    def on_pointer(gesture, x, y):
        if not owner.notifyContextMenu():
            return
        # Claim the sequence so the view does not toggle the row itself.
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        try:
            widget.grab_focus()
            request(row_at(x, y), _point_rect(x, y))
        except Exception:
            logger.exception("context menu request failed")

    click = Gtk.GestureClick()
    click.set_button(Gdk.BUTTON_SECONDARY)
    click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
    click.connect("pressed", lambda g, n, x, y: on_pointer(g, x, y))
    widget.add_controller(click)

    press = Gtk.GestureLongPress()
    press.set_touch_only(True)
    press.connect("pressed", on_pointer)
    widget.add_controller(press)

    def on_key(_widget, _args):
        if not owner.notifyContextMenu():
            return False
        try:
            hit = focus_row()
            if hit is not None:
                anchor = hit[2]
            else:
                anchor = _point_rect(widget.get_width() // 2, widget.get_height() // 2)
            request(hit, anchor)
        except Exception:
            logger.exception("context menu request failed")
        return True

    keys = Gtk.ShortcutController()
    keys.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("<Shift>F10|Menu"),
                                       Gtk.CallbackAction.new(on_key)))
    widget.add_controller(keys)


def _listbox_context_row(listbox, row):
    """Adapt a Gtk.ListBoxRow to the tuple _install_context_menu_triggers expects."""
    if row is None:
        return None

    def select_only():
        if listbox.get_selection_mode() == Gtk.SelectionMode.MULTIPLE:
            listbox.unselect_all()
        listbox.select_row(row)
    return (row.is_selected(), select_only, _widget_rect(row, listbox) or _point_rect(0, 0))


def _build_context_menu(menu, items, top_items, group, state, source, dlg):
    section = Gio.Menu()
    for item in items:
        if not item.visible():
            continue
        if item.isSeparator():
            if section.get_n_items():
                menu.append_section(None, section)
                section = Gio.Menu()
            continue
        label = _convert_mnemonic_to_gtk(item.label())
        name = f"i{len(group.list_actions())}"
        action = Gio.SimpleAction.new(name, None)
        action.set_enabled(item.enabled())
        group.add_action(action)
        if item.isMenu():
            sub = Gio.Menu()
            _build_context_menu(sub, item._children, top_items, group, state, source, dlg)
            entry = Gio.MenuItem.new_submenu(label, sub)
            # A disabled submenu-action makes the submenu entry insensitive.
            entry.set_attribute_value("submenu-action", GLib.Variant.new_string(f"ctx.{name}"))
        else:
            def on_activate(_action, _param, item=item):
                state["picked"] = True
                dlg._post_event(YMenuEvent(item=item, id=context_menu_item_path(item, top_items), widget=source))
            action.connect("activate", on_activate)
            entry = Gio.MenuItem.new(label, f"ctx.{name}")
        gicon = _resolve_gicon(item.iconName()) if item.iconName() else None
        if gicon is not None:
            entry.set_icon(gicon)
        section.append_item(entry)
    if section.get_n_items():
        menu.append_section(None, section)


def _open_context_menu(dlg, items) -> bool:
    """Pop up a Gtk.PopoverMenu for the pending context request of dlg (non-blocking).

    The menu is built from the current item state (a snapshot), so the app may
    change shared YMenuItem objects freely between openings.
    """
    source = getattr(dlg, "_context_menu_source", None)
    anchor = getattr(dlg, "_context_menu_anchor", None)
    if source is None or anchor is None:
        return False
    top_items = context_menu_items(items)
    if not has_selectable_item(top_items):
        return False
    dlg._context_menu_source = None
    dlg._context_menu_anchor = None
    widget, rect = anchor

    old = getattr(dlg, "_context_menu", None)
    if old is not None:
        old[1]["picked"] = True  # replaced, not dismissed
        old[0].popdown()

    state = {"picked": False}
    group = Gio.SimpleActionGroup()
    menu = Gio.Menu()
    _build_context_menu(menu, top_items, top_items, group, state, source, dlg)
    widget.insert_action_group("ctx", group)

    popover = Gtk.PopoverMenu.new_from_model_full(menu, Gtk.PopoverMenuFlags.NESTED)
    popover.set_has_arrow(False)
    popover.set_halign(Gtk.Align.START)
    popover.set_position(Gtk.PositionType.BOTTOM)
    popover.set_parent(widget)
    popover.set_pointing_to(rect)

    def on_closed(_popover):
        # A pick may activate its action after "closed": decide when idle.
        def finish():
            if getattr(dlg, "_context_menu", None) is not None and dlg._context_menu[0] is popover:
                dlg._context_menu = None
                widget.insert_action_group("ctx", None)
            if not state["picked"]:
                dlg._post_event(YWidgetEvent(source, YEventReason.ContextMenuCancelled))
            popover.unparent()
            return False
        GLib.idle_add(finish)
    popover.connect("closed", on_closed)
    dlg._context_menu = (popover, state)
    popover.popup()
    return True
