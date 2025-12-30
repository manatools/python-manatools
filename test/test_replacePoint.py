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

def test_replace_point(backend_name=None):
    """Interactive test for ReplacePoint widget across backends.

    - Creates a dialog with a ReplacePoint
    - Adds an initial child layout and shows it
    - Replaces it at runtime using deleteChildren() and showChild()
    """
    if backend_name:
        root_logger.info("Setting backend to: %s", backend_name)
        os.environ['YUI_BACKEND'] = backend_name
    else:
        root_logger.info("Using auto-detection")
    try:
        from manatools.aui.yui import YUI, YUI_ui 
        import manatools.aui.yui_common as yui

        # Force re-detection
        YUI._instance = None
        YUI._backend = None

        backend = YUI.backend()
        root_logger.info("Using backend: %s", backend.value)

        ui = YUI_ui()
        factory = ui.widgetFactory()

        ui.application().setApplicationTitle(f"Test {backend.value} ReplacePoint")
        dialog = factory.createPopupDialog()
        mainVbox = factory.createVBox(dialog)
        frame = factory.createFrame(mainVbox, "Replace Point here")

        rp = factory.createReplacePoint(frame)

        # Initial child layout
        vbox1 = factory.createVBox(rp)
        # hint: allow vertical stretch to avoid collapsed area in some backends
        import manatools.aui.yui_common as yui
        try:
            vbox1.setStretchable(yui.YUIDimension.YD_VERT, True)
        except Exception:
            pass
        label1 = factory.createLabel(vbox1, "Initial child layout")
        value_btn1 = factory.createPushButton(vbox1, "Value 1")
        #rp.showChild()

        hbox = factory.createHBox(mainVbox)
        replace_button = factory.createPushButton(hbox, "Replace child")
        close_button = factory.createPushButton(hbox, "Close")
        n_call = 0
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
                try:
                    root_logger.info("WidgetEvent from: %s", getattr(wdg, "widgetClass", lambda: "?")())
                except Exception:
                    pass
                if wdg == close_button:
                    dialog.destroy()
                    break
                elif wdg == replace_button:
                    # Replace the child content dynamically
                    n_call = (n_call + 1) % 100
                    root_logger.info("Replacing child layout iteration=%d", n_call)
                    rp.deleteChildren()
                    vbox2 = factory.createVBox(rp)
                    try:
                        vbox2.setStretchable(yui.YUIDimension.YD_VERT, True)
                    except Exception:
                        pass
                    label2 = factory.createLabel(vbox2, f"Replaced child layout ({n_call})")
                    value_btn2 = factory.createPushButton(vbox2, f"Value ({n_call})")
                    rp.showChild()
                elif wdg == value_btn1:
                    # no-op; just ensure button works
                    root_logger.info("Value 1 clicked")
                else:
                    # Handle events from new child too
                    root_logger.debug("Unhandled widget event")
    except Exception as e:
        root_logger.error("Error testing ReplacePoint with backend %s: %s", backend_name, e, exc_info=True)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_replace_point(sys.argv[1])
    else:
        test_replace_point()
