#!/usr/bin/env python3
"""Interactive test for YMultiLineEdit across backends.

- Creates a multiline edit and an OK button to exit.
- Logs value-changed notifications and final value.
"""
import os
import sys
import logging

# Ensure project root on PYTHONPATH
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


def test_multilineedit(backend_name=None):
    if backend_name:
        os.environ['YUI_BACKEND'] = backend_name
        logging.getLogger().info("Set backend to %s", backend_name)
    else:
        logging.getLogger().info("Using auto-detection")
    try:
        from manatools.aui.yui import YUI, YUI_ui
        import manatools.aui.yui_common as yui

        # force re-detection
        YUI._instance = None
        YUI._backend = None

        backend = YUI.backend()
        logging.getLogger().info("Using backend: %s", backend.value)

        ui = YUI_ui()
        factory = ui.widgetFactory()

        ui.application().setApplicationTitle(f"Test {backend.value} MultiLineEdit")
        dlg = factory.createPopupDialog()
        minSize = factory.createMinSize(dlg, 320, 200)
        v = factory.createVBox(minSize)

        mled = factory.createMultiLineEdit(v, "Notes")
        mled.setStretchable(yui.YUIDimension.YD_VERT, True)
        mled.setStretchable(yui.YUIDimension.YD_HORIZ, True)
        ok = factory.createPushButton(v, "OK")

        while True:
            ev = dlg.waitForEvent()
            if not ev:
                continue
            if ev.eventType() == yui.YEventType.CancelEvent:
                dlg.destroy()
                break
            if ev.eventType() == yui.YEventType.WidgetEvent:
                w = ev.widget()
                try:
                    logging.getLogger().debug("WidgetEvent from %s", getattr(w, 'widgetClass', lambda: '?')())
                except Exception:
                    pass
                if w == ok:
                    try:
                        logging.getLogger().info("Final value:\n%s", mled.value())
                    except Exception:
                        logging.getLogger().exception("Failed to read final value")
                    dlg.destroy()
                    break
                # Log value-changed notifications
                try:
                    if hasattr(w, 'widgetClass') and w.widgetClass() == 'YMultiLineEdit':
                        try:
                            logging.getLogger().info("ValueChanged notification: %s", w.value())
                        except Exception:
                            logging.getLogger().exception("Failed to read multiline value on notification")
                except Exception:
                    logging.getLogger().exception("Error handling widget event")

    except Exception as e:
        logging.getLogger().exception("Error in MultiLineEdit test: %s", e)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_multilineedit(sys.argv[1])
    else:
        test_multilineedit()
