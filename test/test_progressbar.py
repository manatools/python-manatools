#!/usr/bin/env python3

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_progressbar(backend_name=None):
    """Test simple dialog with a progress bar and OK button"""
    if backend_name:
        print(f"Setting backend to: {backend_name}")
        os.environ['YUI_BACKEND'] = backend_name
    else:
        print("Using auto-detection")
    try:
        import time
        from manatools.aui.yui import YUI, YUI_ui
        from manatools.aui.yui_common import YTimeoutEvent

        backend = YUI.backend()
        print(f"Using backend: {backend.value}")

        ui = YUI_ui()
        factory = ui.widgetFactory()
        ui.application().setApplicationTitle(f"Progress bar {backend.value} application")
        dialog = factory.createMainDialog()

        vbox = factory.createVBox(dialog)
        pb = factory.createProgressBar(vbox, "Progress", 100)

        # ensure initial value is 0
        pb.setValue(0)

        factory.createPushButton(vbox, "OK")
        dialog.open()

        # Main loop: wait 500ms, increment progress by 1 on timeout.
        # When reaching 100: wait 1s (allowing event handling), reset to 0,
        # then wait 3s before restarting counting. Any non-timeout event (e.g. OK)
        # will break the loop and close the dialog.
        value = 0
        timeout_ms = 500
        phase = 0 # Normal counting
        while True:
            ev = dialog.waitForEvent(timeout_ms)
            if isinstance(ev, YTimeoutEvent):
                # increment
                if phase == 0:
                    value = min(100, value + 1)
                elif phase == 1:
                    value = 0
                    timeout_ms = 3000
                    phase = 3 # Waiting before restart
                elif phase == 3:
                    value = 1
                    timeout_ms = 500
                    phase = 0 # Normal counting
                try:
                    pb.setValue(value)
                except Exception:
                    try:
                        pb.setProperty('value', value)
                    except Exception:
                        pass

                if value >= 100:
                    # wait 1 second (still via waitForEvent to allow user interaction)
                    timeout_ms = 1000
                    phase = 1 # Waiting for reset
            else:
                # any other event (button press, close) break
                break

        dialog.destroy()

    except Exception as e:
        print(f"Error testing ProgressBar with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_progressbar(sys.argv[1])
    else:
        test_progressbar()
