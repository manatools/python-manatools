#!/usr/bin/env python3
"""Interactive test for YIntField across all backends.

- Creates two int fields and two labels that display their values.
- Has an OK button to exit.
- Logs exceptions and backend creation issues.
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


def test_intfield(backend_name=None):
    if backend_name:
        os.environ['YUI_BACKEND'] = backend_name
        logging.getLogger().info("Set backend to %s", backend_name)
    else:
        root_logger.info("Using auto-detection")
    try:
        from manatools.aui.yui import YUI, YUI_ui
        import manatools.aui.yui_common as yui

        # force re-detection
        YUI._instance = None
        YUI._backend = None

        backend = YUI.backend()
        root_logger.info("Using backend: %s", backend.value)

        ui = YUI_ui()
        factory = ui.widgetFactory()

        ui.application().setApplicationTitle(f"Test {backend.value} IntField")
        dlg = factory.createPopupDialog()
        v = factory.createVBox(dlg)

        # Left column with intfields
        h = factory.createHBox(v)
        col1 = factory.createVBox(h)
        col2 = factory.createVBox(h)

        int1 = factory.createIntField(col1, "First", 0, 100, 10)
        int2 = factory.createIntField(col1, "Second", -50, 50, 0)

        lab1 = factory.createLabel(col2, "Value 1: 10")
        lab2 = factory.createLabel(col2, "Value 2: 0")

        ok = factory.createPushButton(v, "OK")

        try:
            # make int fields vertically stretchable if supported
            int1.setStretchable(yui.YUIDimension.YD_VERT, True)
            int2.setStretchable(yui.YUIDimension.YD_VERT, True)
        except Exception:
            pass

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
                    dlg.destroy()
                    break
                # Update labels if values change; some backends post events differently
                try:
                    v1 = int1.value()
                    v2 = int2.value()
                    try:
                        lab1.setValue(f"Value 1: {v1}")
                    except Exception:
                        pass
                    try:
                        lab2.setValue(f"Value 2: {v2}")
                    except Exception:
                        pass
                    logging.getLogger().debug("Int values: %s, %s", v1, v2)
                except Exception:
                    logging.getLogger().exception("Failed to read intfield values")

    except Exception as e:
        logging.getLogger().exception("Error in IntField test: %s", e)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_intfield(sys.argv[1])
    else:
        test_intfield()
