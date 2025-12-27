#!/usr/bin/env python3

"""Example dialog to manually test YRichText widget.

Layout:
- VBox with heading and a RichText widget showing HTML.
- Label displays last activated link.
- OK button closes the dialog.

Run with: `python -m pytest -q test/test_richtext.py::test_richtext_example -s` or run directly.
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


def test_richtext_example(backend_name=None):
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
        logging.getLogger().debug("test_richtext_example: program=%s backend=%s", os.path.basename(sys.argv[0]), getattr(backend, 'value', str(backend)))
    except Exception:
        logging.getLogger().debug("test_richtext_example: program=%s backend=unknown", os.path.basename(sys.argv[0]))

    dlg = factory.createMainDialog()
    vbox = factory.createVBox(dlg)
    factory.createHeading(vbox, "RichText Example")
    factory.createLabel(vbox, "Rich text below with HTML formatting and a link.")

    # Rich text content (HTML)
    html = (
        "<h2>Welcome to <i>RichText</i></h2>"
        "<p>This is <b>bold</b>, <i>italic</i>, and <u>underlined</u> text.</p>"
        "<p>Click the <a href='https://example.com'>example.com</a> link to emit an activation event.</p>"
        "<p>Lists:</p>"
        "<ul><li>Alpha</li><li>Beta</li><li>Gamma</li></ul>"
    )
    rich = factory.createRichText(vbox, html, False)
    try:
        # Enable auto scroll to demonstrate API
        rich.setAutoScrollDown(True)
    except Exception:
        pass

    # Status label for last activated link
    status_label = factory.createLabel(vbox, "Last link: (none)")

    # ok/quit
    ctrl_h = factory.createHBox(vbox)
    ok_btn = factory.createPushButton(ctrl_h, "OK")

    print("Opening RichText example dialog...")

    while True:
        ev = dlg.waitForEvent()
        et = ev.eventType()
        if et == yui.YEventType.CancelEvent:
            dlg.destroy()
            break
        if et == yui.YEventType.WidgetEvent:
            w = ev.widget()
            reason = ev.reason()
            if w == rich and reason == yui.YEventReason.Activated:
                try:
                    # YRichTextQt exposes lastActivatedUrl(); fall back gracefully if not available
                    url = None
                    try:
                        url = rich.lastActivatedUrl()
                    except Exception:
                        url = None
                    status_label.setText(f"Last link: {url if url else '(unknown)'}")
                except Exception:
                    pass
            elif w == ok_btn and reason == yui.YEventReason.Activated:
                dlg.destroy()
                break

    print("Dialog closed")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_richtext_example(sys.argv[1])
    else:
        test_richtext_example()
