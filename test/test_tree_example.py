#!/usr/bin/env python3

"""Example dialog to manually test YTree widgets.

Layout:
- HBox with two trees (left numeric items, right lettered items).
- Button "Swap" that clears both trees and swaps their items, selecting different items.
- Labels show the selected item and selected lists for both trees.

Run with: `python -m pytest -q test/test_tree_example.py::test_tree_example -s` or run directly.
"""

import os
import sys

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import logging

# Configure file logger for this test: write DEBUG logs to '<testname>.log' in cwd
try:
  log_name = os.path.splitext(os.path.basename(__file__))[0] + '.log'
  fh = logging.FileHandler(log_name, mode='w')
  fh.setLevel(logging.DEBUG)
  fh.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s: %(message)s'))
  root_logger = logging.getLogger()
  root_logger.setLevel(logging.DEBUG)
  existing = False
  for h in list(root_logger.handlers):
    try:
      if isinstance(h, logging.FileHandler) and os.path.abspath(getattr(h, 'baseFilename', '')) == os.path.abspath(log_name):
        existing = True
        break
    except Exception:
      pass
  if not existing:
    root_logger.addHandler(fh)
  print(f"Logging test output to: {os.path.abspath(log_name)}")
except Exception as _e:
  print(f"Failed to configure file logger: {_e}")


from manatools.aui.yui import YUI, YUI_ui
import manatools.aui.yui_common as yui


def build_numeric_tree(tree_factory, tree_widget):
    items = []
    for i in range(1, 6):
        itm = yui.YTreeItem(f"Item {i}", is_open=(i == 1))
        for j in range(1, 4):
            sub = yui.YTreeItem(f"SubItem {i}.{j}", parent=itm)
            for k in range(1, 3):
                yui.YTreeItem(f"SubItem {i}.{j}.{k}", parent=sub)
        items.append(itm)
        tree_widget.addItem(itm)
    return items


def build_letter_tree(tree_widget):
    items = []
    letters = ['A', 'B', 'C', 'D', 'E']
    for idx, L in enumerate(letters, start=1):
        itm = yui.YTreeItem(f"Item {L}", is_open=(idx == 1), icon_name=("edit-cut" if L == 'A' else ""))
        for j in range(1, 4):
            sub = yui.YTreeItem(f"SubItem {L}.{j}", parent=itm)
            for k in range(1, 3):
                yui.YTreeItem(f"SubItem {L}.{j}.{k}", parent=sub)
        items.append(itm)
        tree_widget.addItem(itm)
    return items


def test_tree_example(backend_name=None):
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
        logging.getLogger().debug("test_tree_example: program=%s backend=%s", os.path.basename(sys.argv[0]), getattr(backend, 'value', str(backend)))
    except Exception:
        logging.getLogger().debug("test_tree_example: program=%s backend=unknown", os.path.basename(sys.argv[0]))

    # prepare dialog
    dlg = factory.createMainDialog()
    vbox = factory.createVBox(dlg)
    factory.createHeading(vbox, "Tree Swap Example")
    factory.createLabel(vbox, "Two trees side-by-side. Press Swap to exchange items.")

    hbox = factory.createHBox(vbox)
    left_tree = factory.createTree(hbox, "Left Tree")
    right_tree = factory.createTree(hbox, "Right Tree")

    # populate both trees
    left_items = build_numeric_tree(factory, left_tree)
    right_items = build_letter_tree(right_tree)

    # select one item per tree initially
    try:
        # choose a sub-sub item on left and a subitem on right
        left_selected = left_items[1].children() if hasattr(left_items[1], 'children') else None
    except Exception:
        left_selected = None
    try:
        # pick second subitem of first top item on right
        right_selected = right_items[0].children() if hasattr(right_items[0], 'children') else None
    except Exception:
        right_selected = None

    # helper to pick a specific logical item if possible
    def pick_initial_selections():
        # left: choose Item 2.1.1 if exists
        try:
            t = left_items[1]
            # get first child's first child
            sc = list(t.children()) if callable(getattr(t, 'children', None)) else getattr(t, '_children', [])
            if sc:
                sc2 = list(sc[0].children()) if callable(getattr(sc[0], 'children', None)) else getattr(sc[0], '_children', [])
                if sc2:
                    left_tree.selectItem(sc2[0], True)
        except Exception:
            pass
        # right: choose Item A.2 (second subitem of first top item)
        try:
            t = right_items[0]
            sc = list(t.children()) if callable(getattr(t, 'children', None)) else getattr(t, '_children', [])
            if sc and len(sc) >= 2:
                right_tree.selectItem(sc[1], True)
        except Exception:
            pass

    pick_initial_selections()

    # labels showing status
    left_status = factory.createLabel(vbox, "Left selected: None")
    right_status = factory.createLabel(vbox, "Right selected: None")
    both_status = factory.createLabel(vbox, "Left selected list: [] | Right selected list: []")

    # control buttons
    ctrl_h = factory.createHBox(vbox)
    swap_btn = factory.createPushButton(ctrl_h, "Swap")
    quit_btn = factory.createPushButton(factory.createRight(ctrl_h), "Quit")

    # track previous selected labels so we can choose different items after swap
    prev_left_label = None
    prev_right_label = None

    def update_labels():
        try:
            lsel = left_tree.selectedItems()
            rsel = right_tree.selectedItems()
            l_label = lsel[0].label() if lsel else "None"
            r_label = rsel[0].label() if rsel else "None"
            left_status.setText(f"Left selected: {l_label}")
            right_status.setText(f"Right selected: {r_label}")
            left_list = [it.label() for it in lsel]
            right_list = [it.label() for it in rsel]
            both_status.setText(f"Left selected list: {left_list} | Right selected list: {right_list}")
        except Exception:
            pass

    update_labels()

    print("Opening Tree example dialog...")

    while True:
        ev = dlg.waitForEvent()
        et = ev.eventType()
        if et == yui.YEventType.CancelEvent:
            dlg.destroy()
            break
        if et == yui.YEventType.WidgetEvent:
            w = ev.widget()
            reason = ev.reason()
            # selection changed events from either tree
            if w == left_tree and reason == yui.YEventReason.SelectionChanged:
                update_labels()
            elif w == right_tree and reason == yui.YEventReason.SelectionChanged:
                update_labels()
            elif w == swap_btn and reason == yui.YEventReason.Activated:
                # perform swap: capture model items, clear, swap, and set new selections
                root_logger.debug("YTree swapping tree items...")
                try:
                    left_model = list(left_tree._items)
                    right_model = list(right_tree._items)
                except Exception:
                    left_model = []
                    right_model = []
                try:
                    left_tree.deleteAllItems()
                    right_tree.deleteAllItems()
                except Exception:
                    pass
                # add swapped
                try:
                    right_tree.addItems(left_model)
                    left_tree.addItems(right_model)
                except Exception:
                    pass
                #try:
                #    for it in right_model:
                #        left_tree.addItem(it)
                #    for it in left_model:
                #        right_tree.addItem(it)
                #except Exception:
                #    pass
#
                ## select different items than before: pick last top-level in each
                #try:
                #    if left_tree.hasItems():
                #        # pick last top-level's first sub-sub if available
                #        it = left_tree._items[-1]
                #        children = list(getattr(it, 'children', lambda: [])()) if callable(getattr(it, 'children', None)) else getattr(it, '_children', [])
                #        target = None
                #        if children:
                #            sc = children[0]
                #            sc2 = list(getattr(sc, 'children', lambda: [])()) if callable(getattr(sc, 'children', None)) else getattr(sc, '_children', [])
                #            if sc2:
                #                target = sc2[-1]
                #        if target is None:
                #            target = it
                #        left_tree.selectItem(target, True)
                #except Exception:
                #    pass
                #try:
                #    if right_tree.hasItems():
                #        it = right_tree._items[-1]
                #        children = list(getattr(it, 'children', lambda: [])()) if callable(getattr(it, 'children', None)) else getattr(it, '_children', [])
                #        target = None
                #        if children and len(children) >= 2:
                #            target = children[1]
                #        elif children:
                #            target = children[0]
                #        if target is None:
                #            target = it
                #        right_tree.selectItem(target, True)
                #except Exception:
                #    pass

                update_labels()
            elif w == quit_btn and reason == yui.YEventReason.Activated:
                dlg.destroy()
                break

    print("Dialog closed")


if __name__ == '__main__':
    # allow running directly
    if len(sys.argv) > 1:
        test_tree_example(sys.argv[1])
    else:
        test_tree_example()
