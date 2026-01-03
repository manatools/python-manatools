#!/usr/bin/env python3

import os
import sys

# Add parent directory to path
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

def test_image(backend_name=None):
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
        dialog = factory.createPopupDialog()
        vbox = factory.createVBox(dialog)
        factory.createHeading(vbox, "Image widget demo")

        # Use an example image path if available (relative to project), otherwise empty
        example = os.path.join(os.path.dirname(__file__), '..', 'share/images', 'manatools.png')
        example = os.path.abspath(example)
        if not os.path.exists(example):
            example = ""

        img = factory.createImage(vbox, example)
        # allow image to expand horizontally
        img.setStretchable(yui.YUIDimension.YD_HORIZ, True)
        img.setStretchable(yui.YUIDimension.YD_VERT, True)
        img.setAutoScale(True)

        # OK button
        hbox = factory.createHBox(vbox)
        ok = factory.createPushButton(hbox, "OK")
        close = factory.createPushButton(hbox, "Close")

        dialog.open()
        while True:
          event = dialog.waitForEvent()
          if not event:
            continue
          typ = event.eventType()
          if typ == yui.YEventType.CancelEvent:
                dialog.destroy()
                break
          elif typ == yui.YEventType.WidgetEvent:
              wdg = event.widget()
              if wdg == close:
                  dialog.destroy()
                  break
              elif wdg == ok:
                  dialog.destroy()
                  break

    except Exception as e:
        print(f"Error testing Image with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_image(sys.argv[1])
    else:
        test_image()
