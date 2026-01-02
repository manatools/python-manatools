#!/usr/bin/env python3

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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

        ui = YUI_ui()
        ui.yApp().setApplicationTitle("Spacing Demo")
        factory = ui.widgetFactory()
        dialog = factory.createMainDialog()

        vbox = factory.createVBox(dialog)
        factory.createLabel(vbox, "Spacing demo: pixels as unit; curses converts to chars.")

        # Horizontal spacing line: label - spacing(50px, fixed) - button - spacing(80px, stretch min)
        hbox = factory.createHBox(vbox)
        factory.createLabel(hbox, "LeftLabel")
        factory.createSpacing(hbox, yui.YUIDimension.YD_HORIZ, False, 50.0)
        factory.createPushButton(hbox, "Click Me")
        factory.createSpacing(hbox, yui.YUIDimension.YD_HORIZ, True, 80.0)
        factory.createCheckBox(hbox, "Check", False)

        # Vertical spacing between rows (24px ~= 1 char in curses)
        factory.createSpacing(vbox, yui.YUIDimension.YD_VERT, False, 24.0)

        # Another row with stretchable vertical spacing on both sides
        hbox2 = factory.createHBox(vbox)
        factory.createSpacing(hbox2, yui.YUIDimension.YD_HORIZ, True, 20.0)
        factory.createLabel(hbox2, "Centered by spacers")
        factory.createSpacing(hbox2, yui.YUIDimension.YD_HORIZ, True, 20.0)

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
