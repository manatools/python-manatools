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


def test_file_dialogs(backend_name=None):
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
        app = ui.app()
        factory = ui.widgetFactory()
        dialog = factory.createPopupDialog()

        vbox = factory.createVBox(dialog)
        factory.createHeading(vbox, "File dialog test")

        # main area: HBox with multiline edit on left and buttons on right
        h = factory.createHBox(vbox)
        mled = factory.createMultiLineEdit(h, "File content")
        mled.setStretchable(yui.YUIDimension.YD_VERT, True)
        mled.setStretchable(yui.YUIDimension.YD_HORIZ, True)

        right = factory.createVBox(h)
        open_btn = factory.createPushButton(right, "Open")
        save_btn = factory.createPushButton(right, "Save")
        testdir_btn = factory.createPushButton(right, "Test Dir")

        dir_label = factory.createLabel(vbox, "No dir selected")
        dir_label.setStretchable(yui.YUIDimension.YD_VERT, False)
        dir_label.setStretchable(yui.YUIDimension.YD_HORIZ, True)

        factory.createSpacing(vbox, yui.YUIDimension.YD_VERT, False, 10)
        close_btn = factory.createPushButton(factory.createHVCenter(vbox), "Close")

        # wire events in the event loop by checking WidgetEvent and comparing widgets
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
                if wdg == open_btn:
                    # ask for text file
                    fname = app.askForExistingFile("", "*.txt", "Open text file")
                    if fname:
                        try:
                            with open(fname, 'r', encoding='utf-8') as f:
                                data = f.read()
                            mled.setValue(data)
                        except Exception as e:
                            print(f"Failed to read file: {e}")
                elif wdg == save_btn:
                    fname = app.askForSaveFileName("", "*.txt", "Save text file")
                    if fname:
                        try:
                            data = mled.value()
                            with open(fname, 'w', encoding='utf-8') as f:
                                f.write(data)
                        except Exception as e:
                            print(f"Failed to save file: {e}")
                elif wdg == testdir_btn:
                    d = app.askForExistingDirectory("", "Select directory")
                    if d:
                        dir_label.setText(d)
                elif wdg == close_btn:
                    dialog.destroy()
                    break

    except Exception as e:
        print(f"Error testing file dialogs with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_file_dialogs(sys.argv[1])
    else:
        test_file_dialogs()
