#!/usr/bin/env python3

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_slide(backend_name=None):
    """Interactive test showcasing Slider widget."""
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
        factory.createHeading(vbox, "Slider Test")
        factory.createLabel(vbox, f"Backend: {backend.value}")

        # Create slider
        slider = factory.createSlider(vbox, "Volume:", 0, 100, 25)

        # Show current value
        val_label = factory.createLabel(vbox, "Value: 25")

        # Buttons
        h = factory.createHBox(vbox)
        ok_btn = factory.createPushButton(h, "OK")
        close_btn = factory.createPushButton(h, "Close")

        print("\nOpening Slider test dialog...")

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
                    print("OK clicked. Final value:", slider.value())
                if wdg == slider:
                    if reason == yui.YEventReason.ValueChanged:
                        val_label.setText(f"Value: {slider.value()}")
                        print("ValueChanged:", slider.value())
                    elif reason == yui.YEventReason.Activated:
                        print("Activated at:", slider.value())
    except Exception as e:
        print(f"Error testing Slider with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_slide(sys.argv[1])
    else:
        test_slide()
