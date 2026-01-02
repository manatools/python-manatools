#!/usr/bin/env python3

import os
import sys
import logging

# Add parent directory to path
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

def test_Spacing(backend_name=None):
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

        # Basic logging setup
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s: %(message)s")

        ui = YUI_ui()
        ui.yApp().setApplicationTitle("Spacing Demo")
        factory = ui.widgetFactory()
        dialog = factory.createMainDialog()

        vbox = factory.createVBox(dialog)
        factory.createHeading(vbox, "Spacing demo: pixels as unit; curses converts to chars.")

        factory.createLabel(vbox, "Next row is [LeftLabel, spacing 50px, button, spacing 80px (stretchable), checkbox]")
        # Horizontal spacing line: label - spacing(50px, fixed) - button - spacing(80px, stretch min)
        hbox = factory.createHBox(vbox)
        factory.createLabel(hbox, "LeftLabel")
        factory.createSpacing(hbox, yui.YUIDimension.YD_HORIZ, False, 50)
        factory.createPushButton(hbox, "Click Me")
        # stretchable spacing should take remaining width between button and checkbox
        s = factory.createSpacing(hbox, yui.YUIDimension.YD_HORIZ, True, 80)
        factory.createCheckBox(hbox, "Check", False)

        factory.createLabel(vbox, "Next vertical spacing 24px (fixed) between rows")
        # Vertical spacing between rows (24px ~= 1 char in curses)
        factory.createSpacing(vbox, yui.YUIDimension.YD_VERT, False, 24)

        # Another row with stretchable vertical spacing on both sides
        factory.createLabel(vbox, "Next row is [spacing 20px (stretchable), centered button, spacing 20px (stretchable)]")
        hbox2 = factory.createHBox(vbox)
        factory.createSpacing(hbox2, yui.YUIDimension.YD_HORIZ, True, 20)
        btn = factory.createPushButton(hbox2, "Centered by spacers")
        btn.setStretchable(yui.YUIDimension.YD_HORIZ, False)
        btn.setStretchable(yui.YUIDimension.YD_VERT, False)
        factory.createSpacing(hbox2, yui.YUIDimension.YD_HORIZ, True, 20)
        factory.createLabel(vbox, "Next vertical spacing 20px (stretchable) between rows")
        # add a vertical stretch spacer below the row to demonstrate vertical expansion
        factory.createSpacing(vbox, yui.YUIDimension.YD_VERT, True, 20)

        # OK button
        ok = factory.createPushButton(vbox, "OK")
        ok.setStretchable(yui.YUIDimension.YD_HORIZ, True)
        ok.setStretchable(yui.YUIDimension.YD_VERT, False)

        dialog.open()
        event = dialog.waitForEvent()
        dialog.destroy()

    except Exception as e:
        print(f"Error testing Spacing with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_Spacing(sys.argv[1])
    else:
        test_Spacing()
