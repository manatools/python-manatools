#!/usr/bin/env python3
"""Interactive test for context menus across backends.

- Table, tree and multi-selection box report right-clicks
  (F2 on the cursor row in ncurses) via setNotifyContextMenu(True).
- One menu is built once and reused for every row and widget; it is
  adjusted per row before openContextMenu():
  "Rename" shows the row label, "Delete" is disabled on locked rows,
  "Debug" is visible only while the checkbox is on.
- The menu has a separator, a disabled item and nested submenus.
- "Table menu" checkbox switches the table's context menu on/off live.
- Every event is logged and shown in the status label.
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


def test_context_menu_example(backend_name=None):
    if backend_name:
        os.environ['MUI_BACKEND'] = backend_name

    # Ensure fresh YUI detection
    YUI._instance = None
    YUI._backend = None

    ui = YUI_ui()
    factory = ui.widgetFactory()
    app = ui.app()

    try:
        backend = YUI.backend()
        root_logger.debug("test_context_menu_example: program=%s backend=%s", os.path.basename(sys.argv[0]), getattr(backend, 'value', str(backend)))
    except Exception:
        root_logger.debug("test_context_menu_example: program=%s backend=unknown", os.path.basename(sys.argv[0]))

    app.setApplicationTitle(f"Context Menu {backend.value} Test")
    dlg = factory.createMainDialog()
    minsize = factory.createMinSize(dlg, 720, 520)
    vbox = factory.createVBox(minsize)

    hint = "F2 opens the context menu" if app.isTextMode() else "Right-click a row (Shift+F10 / Menu key)"
    factory.createLabel(vbox, hint)

    hbox = factory.createHBox(vbox)

    # Table
    header = yui.YTableHeader()
    header.addColumn('name')
    header.addColumn('size', alignment=yui.YAlignmentType.YAlignEnd)
    table = factory.createTable(hbox, header)
    for i, name in enumerate(["alpha", "beta (locked)", "gamma", "delta", "epsilon (locked)"]):
        itm = yui.YTableItem(name)
        itm.addCell(name)
        itm.addCell(str((i + 1) * 1024))
        table.addItem(itm)
    table.setNotifyContextMenu(True)

    # Tree
    tree = factory.createTree(hbox, "Folders")
    for i in range(3):
        top = yui.YTreeItem(f"Folder {i + 1}", is_open=(i == 0))
        for j in range(2):
            yui.YTreeItem(f"File {i + 1}.{j + 1}" + (" (locked)" if j == 1 else ""), parent=top)
        tree.addItem(top)
    tree.setNotifyContextMenu(True)

    # Multi-selection box
    sbox = factory.createMultiSelectionBox(hbox, "Tags")
    for tag in ["red", "green", "blue (locked)", "yellow"]:
        sbox.addItem(tag)
    sbox.setNotifyContextMenu(True)

    # One menu, built once, reused for every row and widget
    menu = yui.YMenuItem("context", is_menu=True)
    item_open = menu.addItem("&Open", icon_name="document-open")
    item_rename = menu.addItem("&Rename")
    menu.addSeparator()
    item_delete = menu.addItem("&Delete", icon_name="edit-delete")
    item_never = menu.addItem("Never enabled")
    item_never.setEnabled(False)
    move_menu = menu.addMenu("&Move to")
    move_menu.addItem("&Trash", icon_name="user-trash")
    move_menu.addItem("&Archive")
    move_menu.addSeparator()
    other_menu = move_menu.addMenu("&Other")
    other_menu.addItem("&Elsewhere")
    item_debug = menu.addItem("De&bug info")

    ctrl_h = factory.createHBox(vbox)
    table_toggle = factory.createCheckBox(ctrl_h, "&Table menu", True)
    debug_toggle = factory.createCheckBox(ctrl_h, "Show debu&g item", False)

    status_label = factory.createLabel(vbox, "Last event: (none)")
    ok_btn = factory.createPushButton(factory.createHCenter(vbox), "&OK")

    def target_labels(w):
        return [it.label() for it in (w.selectedItems() or [])]

    def show(text):
        root_logger.info(text)
        status_label.setValue(f"Last event: {text}")

    root_logger.info("Opening context menu example dialog...")

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
            elif w == table_toggle:
                table.setNotifyContextMenu(table_toggle.isChecked())
                show(f"table context menu {'on' if table.notifyContextMenu() else 'off'}")
            elif reason == yui.YEventReason.ContextMenuActivated:
                # The row under the pointer (or cursor) is already selected here
                labels = target_labels(w)
                locked = any("(locked)" in lbl for lbl in labels)
                # Per-row tweaks on the shared items, before opening
                item_rename.setLabel(f"&Rename '{labels[0]}'" if len(labels) == 1 else "&Rename")
                item_rename.setEnabled(len(labels) == 1)
                item_delete.setEnabled(bool(labels) and not locked)
                item_debug.setVisible(debug_toggle.isChecked())
                opened = app.openContextMenu(menu)
                show(f"{w.widgetClass()} context request on {labels or '(no row)'}; menu opened={opened}")
            elif reason == yui.YEventReason.ContextMenuCancelled:
                show(f"{w.widgetClass()} context menu dismissed")
            elif reason == yui.YEventReason.SelectionChanged:
                root_logger.debug("%s selection: %s", w.widgetClass(), target_labels(w))
        elif et == yui.YEventType.MenuEvent:
            source = ev.widget()
            if source is None:
                continue  # not a context menu (e.g. rich text link)
            item = ev.item()
            what = target_labels(source)
            show(f"{ev.id()} on {source.widgetClass()} {what}")
            if item is item_open:
                root_logger.debug("Open %s", what)
            elif item is item_delete:
                root_logger.debug("Delete %s", what)

    root_logger.info("Dialog closed")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_context_menu_example(sys.argv[1])
    else:
        test_context_menu_example()
