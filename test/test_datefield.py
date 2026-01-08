#!/usr/bin/env python3

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_datefield(backend_name=None):
    """Interactive test for YDateField widget."""
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
        factory.createHeading(vbox, "DateField Test")
        factory.createLabel(vbox, f"Backend: {backend.value}")

        # Create datefield
        df = factory.createDateField(vbox, "Select Date:")

        # Buttons
        h = factory.createHBox(vbox)
        ok_btn = factory.createPushButton(h, "OK")
        close_btn = factory.createPushButton(h, "Close")

        print("\nOpening DateField test dialog...")

        while True:
            ev = dialog.waitForEvent()
            et = ev.eventType()
            if et == yui.YEventType.CancelEvent:
                dialog.destroy()
                break
            elif et == yui.YEventType.WidgetEvent:
                wdg = ev.widget()
                reason = ev.reason()
                if wdg == close_btn and reason == yui.YEventReason.Activated:
                    dialog.destroy()
                    break
                if wdg == ok_btn and reason == yui.YEventReason.Activated:
                    print("OK clicked. Final date:", df.value())
                    dialog.destroy()
                    break
    except Exception as e:
        print(f"Error testing DateField with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_datefield(sys.argv[1])
    else:
        test_datefield()
