#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple interactive test for YLabel auto-wrap and output field.

Shows a dialog with three labels:
- Normal label
- Wrapped label (autoWrap=True) with 12-line long content
- Output-field label (isOutputField=True)

Run this test manually to visually verify wrapping behavior in the available backend.
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


def make_long_text(lines=12):
    parts = [f"Line {i+1}: The quick brown fox jumps over the lazy dog." for i in range(lines)]
    return "\n".join(parts)


def test_label_wrap_example(backend_name=None):
    if backend_name:
        os.environ['YUI_BACKEND'] = backend_name

    # Ensure fresh YUI detection
    YUI._instance = None
    YUI._backend = None

    ui = YUI_ui()
    factory = ui.widgetFactory()

    try:
        backend = YUI.backend()
        root_logger.debug("test_label_wrap_example: program=%s backend=%s", os.path.basename(sys.argv[0]), getattr(backend, 'value', str(backend)))
    except Exception:
        root_logger.debug("test_label_wrap_example: program=%s backend=unknown", os.path.basename(sys.argv[0]))

    dlg = factory.createMainDialog()
    vbox = factory.createVBox(dlg)

    # Normal label
    lab1 = factory.createLabel(vbox, "First label: normal text.")

    # Wrapped label with 12 lines
    long_text = make_long_text(12)
    lab2 = factory.createLabel(vbox, long_text)
    try:
        lab2.setAutoWrap(True)
    except Exception:
        pass

    # Output-field label
    lab3 = factory.createLabel(vbox, "Output-field label: non-editable.", isOutputField=True)

    # ok/quit
    ctrl_h = factory.createHBox(vbox)
    ok_btn = factory.createPushButton(ctrl_h, "OK")

    root_logger.info("Opening Label wrap example dialog...")

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

    root_logger.info("Dialog closed")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_label_wrap_example(sys.argv[1])
    else:
        test_label_wrap_example()
