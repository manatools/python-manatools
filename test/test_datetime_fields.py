#!/usr/bin/env python3

import os
import sys
import logging
import datetime


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


def test_datefield(backend_name=None):
    """Interactive test for YDateField and YTimeField widgets."""
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
        factory.createHeading(vbox, "Date/TimeField Test")
        factory.createLabel(vbox, f"Backend: {backend.value}")

        # Create datefield
        df = factory.createDateField(vbox, "Select Date:")
        now = datetime.datetime.now()
        df.setValue(now.strftime("%Y-%m-%d"))

        # Create timefield
        try:
            tf = factory.createTimeField(vbox, "Select Time:")
            tf.setValue(now.strftime("%H:%M:%S"))
        except Exception as e:
            tf = None
            logging.getLogger(__name__).exception("Failed to create TimeField: %s", e)

        # Buttons
        h = factory.createHBox(vbox)
        ok_btn = factory.createPushButton(h, "OK")
        close_btn = factory.createPushButton(h, "Close")

        print("\nOpening Date/TimeField test dialog...")

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
                if wdg == ok_btn and reason == yui.YEventReason.Activated:
                    print("OK clicked. Final date:", df.value())
                    if tf is not None:
                        print("Final time:", tf.value())
                    break
        logging.info("Date: %s", df.value())
        if tf is not None:
            logging.info("Time: %s", tf.value())
        dialog.destroy()
    except Exception as e:
        print(f"Error testing DateField with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_datefield(sys.argv[1])
    else:
        test_datefield()
