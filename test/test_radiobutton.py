#!/usr/bin/env python3

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_radiobutton(backend_name=None):
    """Test dialog with 3 radio buttons, a label showing selection, and OK button"""
    if backend_name:
        print(f"Setting backend to: {backend_name}")
        os.environ['YUI_BACKEND'] = backend_name
    else:
        print("Using auto-detection")

    try:
        import time
        from manatools.aui.yui import YUI, YUI_ui
        from manatools.aui.yui_common import YTimeoutEvent, YWidgetEvent, YCancelEvent

        backend = YUI.backend()
        print(f"Using backend: {backend.value}")

        ui = YUI_ui()
        factory = ui.widgetFactory()
        ui.application().setApplicationTitle(f"RadioButton {backend.value} test")

        dialog = factory.createMainDialog()
        vbox = factory.createVBox(dialog)

        # First radio group (3 options)
        frame = factory.createFrame(vbox, "Options")
        inner1 = factory.createVBox(frame)

        rb1 = factory.createRadioButton(inner1, "Option 1", False)
        rb2 = factory.createRadioButton(inner1, "Option 2", True)
        rb3 = factory.createRadioButton(inner1, "Option 3", False)
        selected_label1 = factory.createLabel(vbox, "Selected: Option 2")
        
        # Second radio group (2 test options)
        frame2 = factory.createFrame(vbox, "Tests")
        inner2 = factory.createVBox(frame2)
        tr1 = factory.createRadioButton(inner2, "Test 1", True)
        tr2 = factory.createRadioButton(inner2, "Test 2", False)

        selected_label2 = factory.createLabel(vbox, "Selected: Test 1")

        ok_button = factory.createPushButton(vbox, "OK")

        dialog.open()

        # Event loop: wait for events; on widget events update the label;
        # OK button closes the dialog.
        while True:
            ev = dialog.waitForEvent(500)
            if isinstance(ev, YTimeoutEvent):
                continue
            if isinstance(ev, YCancelEvent):
                break
            if isinstance(ev, YWidgetEvent):
                w = ev.widget()
                # If OK pressed -> exit
                if w == ok_button:
                    break
                elif w in (rb1, rb2, rb3):
                    selected_label1.setText(f"Selected: {w.label()}")
                elif w in (tr1, tr2):
                    selected_label2.setText(f"Selected: {w.label()}")

        dialog.destroy()

    except Exception as e:
        print(f"Error testing RadioButton with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_radiobutton(sys.argv[1])
    else:
        test_radiobutton()
