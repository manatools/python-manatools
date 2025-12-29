#!/usr/bin/env python3
"""Interactive test for YMenuBar across backends.

- Creates a dialog with a menu bar and a status label.
- File menu: Open (enabled), Close (disabled), Exit.
- Selecting Open disables Open and enables Close; selecting Close reverses.
- Exit closes the dialog.
- Edit menu: Copy, Paste, Cut.
- More menu: submenus to verify nested menus.
- OK button exits.
"""
import os
import sys
import logging

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    log_name = os.path.splitext(os.path.basename(__file__))[0] + '.log'
    logFormatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s: %(message)s')
    root_logger = logging.getLogger()
    fileHandler = logging.FileHandler(log_name, mode='w')
    fileHandler.setFormatter(logFormatter)
    root_logger.addHandler(fileHandler)
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    root_logger.addHandler(consoleHandler)
    consoleHandler.setLevel(logging.INFO)
    root_logger.setLevel(logging.DEBUG)
except Exception as _e:
    logging.getLogger().exception("Failed to configure file logger: %s", _e)

from manatools.aui.yui import YUI, YUI_ui
import manatools.aui.yui_common as yui


def test_menubar_example(backend_name=None):
    if backend_name:
        os.environ['YUI_BACKEND'] = backend_name

    # Ensure fresh YUI detection
    YUI._instance = None
    YUI._backend = None

    ui = YUI_ui()
    factory = ui.widgetFactory()

    # Log program name and detected backend
    try:
        backend = YUI.backend()
        root_logger.debug("test_menubar_example: program=%s backend=%s", os.path.basename(sys.argv[0]), getattr(backend, 'value', str(backend)))
    except Exception:
        root_logger.debug("test_menubar_example: program=%s backend=unknown", os.path.basename(sys.argv[0]))

    ui.app().setApplicationTitle(f"Menu Bar {backend.value} Test")
    dlg = factory.createMainDialog()
    vbox = factory.createVBox(dlg)

    # Menu bar
    menubar = factory.createMenuBar(vbox)

    # File menu
    file_menu = menubar.addMenu("File", icon_name="application-menu")
    item_open = menubar.addItem(file_menu, "Open", icon_name="document-open", enabled=True)
    item_close = menubar.addItem(file_menu, "Close", icon_name="window-close", enabled=False)
    file_menu.addSeparator()
    item_exit = menubar.addItem(file_menu, "Exit", icon_name="application-exit", enabled=True)

    # Edit menu
    edit_menu = menubar.addMenu("Edit")
    menubar.addItem(edit_menu, "Copy", icon_name="edit-copy")
    menubar.addItem(edit_menu, "Paste", icon_name="edit-paste")
    menubar.addItem(edit_menu, "Cut", icon_name="edit-cut")

    # More menu with submenus
    more_menu = menubar.addMenu("More")
    sub1 = more_menu.addMenu("Submenu 1")
    sub1.addItem("One")
    sub1.addItem("Two")
    sub2 = more_menu.addMenu("Submenu 2")
    sub2.addItem("Alpha")
    sub2.addItem("Beta")
    sub3 = sub2.addMenu("Submenu 2.1")
    sub3.addItem("Info")
    sub2.addSeparator()
    enableSubMenu3 = sub2.addItem("Enable Submenu 3")
    sub2.addSeparator()
    to_change_menu = sub2.addItem("To Change menu")
    # Hidden submenu for testing visibility
    sub4 = more_menu.addMenu("Submenu 3")
    sub4.addItem("Was Hidden")
#    menubar.setItemVisible(sub4 ,False)
    sub4.setVisible(False)

    change_menu = yui.YMenuItem("Change", is_menu = True)
    to_more_menu = change_menu.addItem("To More menu")
    
    menu1 = [file_menu, edit_menu, more_menu]
    menu2 = [file_menu, edit_menu, change_menu]
    # Status label
    status_label = factory.createLabel(vbox, "Selected: (none)")

    # OK button
    ctrl_h = factory.createHBox(vbox)
    ok_btn = factory.createPushButton(ctrl_h, "OK")

    root_logger.info("Opening MenuBar example dialog...")

    while True:
        ev = dlg.waitForEvent()
        et = ev.eventType()
        if et == yui.YEventType.CancelEvent:
            dlg.destroy()
            break
        elif et == yui.YEventType.WidgetEvent:
            w = ev.widget()
            reason = ev.reason()
            if w == ok_btn and reason == yui.YEventReason.Activated:
                dlg.destroy()
                break
        elif et == yui.YEventType.MenuEvent:
            path = ev.id() if ev.id() else '(none)'
            status_label.setValue(f"Selected: {path}")
            item = ev.item()
            if item is not None:
                if item == item_open:
                    root_logger.debug("Menu item selected: File/Open")
                    menubar.setItemEnabled(item_open, False)
                    menubar.setItemEnabled(item_close, True)
                elif item == item_close:
                    root_logger.debug("Menu item selected: File/Close")
                    menubar.setItemEnabled(item_open, True)
                    menubar.setItemEnabled(item_close, False)
                elif item == item_exit:
                    root_logger.info("Menu item selected: File/Exit")
                    dlg.destroy()
                    break
                elif item == enableSubMenu3:
                    root_logger.info(f"Menu item selected: {item.label()}")                
                    #menubar.setItemVisible(sub4, not sub4.visible())
                    sub4.setVisible(not sub4.visible())
                    enableSubMenu3.setLabel("Disable Submenu 3" if sub4.visible() else "Enable Submenu 3")
                    menubar.rebuildMenus() # more_menu
                elif item == to_change_menu:
                    root_logger.info(f"Menu item selected: {item.label()}")
                    menubar.deleteMenus()
                    for m in menu2:
                        menubar.addMenu(menu=m)
                elif item == to_more_menu:
                    root_logger.info(f"Menu item selected: {item.label()}")
                    menubar.deleteMenus()
                    for m in menu1:
                        menubar.addMenu(menu=m)                    

    root_logger.info("Dialog closed")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_menubar_example(sys.argv[1])
    else:
        test_menubar_example()
