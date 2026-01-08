#!/usr/bin/env python3

import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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


def test_logview(backend_name=None):
    """Interactive test for YLogView widget."""
    if backend_name:
        print(f"Setting backend to: {backend_name}")
        os.environ['YUI_BACKEND'] = backend_name
    else:
        print("Using auto-detection")

    try:
        from manatools.aui.yui import YUI, YUI_ui
        import manatools.aui.yui_common as yui

        # Force re-detection
        YUI._instance = None
        YUI._backend = None

        backend = YUI.backend()
        print(f"Using backend: {backend.value}")

        ui = YUI_ui()
        factory = ui.widgetFactory()
        dialog = factory.createMainDialog()

        vbox = factory.createVBox(dialog)
        factory.createHeading(vbox, "LogView Test")
        factory.createLabel(vbox, f"Backend: {backend.value}")

        # Create LogView
        lv = factory.createLogView(vbox, "Log:", 10, 50)
        lv.appendLines("Initial line 1\nInitial line 2")

        # Buttons
        h = factory.createHBox(vbox)
        add_btn = factory.createPushButton(h, "Append 5 lines")
        clear_btn = factory.createPushButton(h, "Clear")
        close_btn = factory.createPushButton(h, "Close")

        print("\nOpening LogView test dialog...")

        counter = 0
        while True:
            ev = dialog.waitForEvent()
            et = ev.eventType()
            if et == yui.YEventType.CancelEvent:
                break
            elif et == yui.YEventType.WidgetEvent:
                wdg = ev.widget()
                reason = ev.reason()
                if wdg == close_btn and reason == yui.YEventReason.Activated:
                    break
                if wdg == clear_btn and reason == yui.YEventReason.Activated:
                    lv.clearText()
                if wdg == add_btn and reason == yui.YEventReason.Activated:
                    lines = []
                    for i in range(5):
                        counter += 1
                        lines.append(f"line {counter}")
                    lv.appendLines("\n".join(lines))
        dialog.destroy()
    except Exception as e:
        print(f"Error testing LogView with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_logview(sys.argv[1])
    else:
        test_logview()
