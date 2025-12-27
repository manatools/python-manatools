#!/usr/bin/env python3

"""Example dialog to manually test YTable widgets.

Layout:
- HBox with two tables (left checkboxed, right multi-selection).
- Labels show selected rows and checkbox states.
- OK button closes the dialog.

Run with: `python -m pytest -q test/test_table.py::test_table_example -s` or run directly.
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


def build_left_checkbox_table(factory, table_widget):
    items = []
    for i in range(1, 7):
        itm = yui.YTableItem(f"Row {i}")
        itm.addCell(str(i))
        itm.addCell(f"test {i}")
        # third column is checkbox column
        itm.addCell(False if i % 2 == 0 else True)
        items.append(itm)
        table_widget.addItem(itm)
    return items


def build_right_multi_table(factory, table_widget):
    items = []
    for i in range(1, 7):
        itm = yui.YTableItem(f"Name {i}")
        itm.addCells(f"Name {i}", f"Addr {i} Street", f"{10000+i}", f"Town {i}")
        items.append(itm)
        table_widget.addItem(itm)
    return items


def test_table_example(backend_name=None):
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
        logging.getLogger().debug("test_table_example: program=%s backend=%s", os.path.basename(sys.argv[0]), getattr(backend, 'value', str(backend)))
    except Exception:
        logging.getLogger().debug("test_table_example: program=%s backend=unknown", os.path.basename(sys.argv[0]))

    dlg = factory.createMainDialog()
    vbox = factory.createVBox(dlg)
    factory.createHeading(vbox, "Table Example")
    factory.createLabel(vbox, "Two tables side-by-side. Left has checkbox column.")

    hbox = factory.createHBox(vbox)

    # left: checkbox table header (third column is checkbox) with alignment:
    # first column right aligned, checkbox column centered
    left_header = yui.YTableHeader()
    left_header.addColumn('num.', alignment=yui.YAlignmentType.YAlignEnd)
    left_header.addColumn('info', alignment=yui.YAlignmentType.YAlignBegin)
    left_header.addColumn('', checkBox=True, alignment=yui.YAlignmentType.YAlignCenter)
    left_table = factory.createTable(hbox, left_header)
    #left_table.setEnabled(False)

    # right: multi-selection table
    right_header = yui.YTableHeader()
    right_header.addColumn('name')
    right_header.addColumn('address')
    right_header.addColumn('zip code')
    right_header.addColumn('town')
    right_table = factory.createTable(hbox, right_header, True)

    # populate
    left_items = build_left_checkbox_table(factory, left_table)
    right_items = build_right_multi_table(factory, right_table)

    # status labels
    sel_label = factory.createLabel(vbox, "Selected: None")
    chk_label = factory.createLabel(vbox, "Checked rows: []")

    # ok/quit
    ctrl_h = factory.createHBox(vbox)
    ok_btn = factory.createPushButton(ctrl_h, "OK")

    def update_labels(checked_item=None):
        try:
            sel = right_table.selectedItems()
            sel_text = [it.label() for it in sel]
            sel_label.setText(f"Selected: {sel_text}")
            # left table checked states
            checked = []
            for it in left_items:
                if it.cellCount() >= 3 and it.cell(2).checked():
                    checked.append(it.label(0))
            if checked_item is not None:
                chk_label.setText(f"Checked rows: {checked} | Selected{checked_item.label(0)}: checked:{checked_item.checked(2)}")
            else:
                chk_label.setText(f"Checked rows: {checked}")
        except Exception:
            pass

    update_labels()

    print("Opening Table example dialog...")

    while True:
        ev = dlg.waitForEvent()
        et = ev.eventType()
        if et == yui.YEventType.CancelEvent:
            dlg.destroy()
            break
        if et == yui.YEventType.WidgetEvent:
            w = ev.widget()
            reason = ev.reason()
            if w == right_table and reason == yui.YEventReason.SelectionChanged:
                update_labels()
            elif w == left_table and reason == yui.YEventReason.ValueChanged:
                sel = left_table.changedItem()
                #root_logger.debug(f"Left table checkbox changed, item: {sel.label(0) if sel else 'None'}")
                update_labels(sel)
            elif w == ok_btn and reason == yui.YEventReason.Activated:
                dlg.destroy()
                break

    print("Dialog closed")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_table_example(sys.argv[1])
    else:
        test_table_example()
