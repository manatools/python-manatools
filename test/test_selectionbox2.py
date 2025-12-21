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
    # Avoid adding duplicate file handlers for repeated imports
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

def test_two_selectionbox(backend_name=None):
    """Two selection boxes side by side; label below shows which box and value."""
    if backend_name:
        print(f"Setting backend to: {backend_name}")
        os.environ['YUI_BACKEND'] = backend_name
    else:
        print("Using auto-detection")

    try:
        from manatools.aui.yui import YUI, YUI_ui
        import manatools.aui.yui_common as yui

        backend = YUI.backend()
        print(f"Using backend: {backend.value}")

        ui = YUI_ui()
        factory = ui.widgetFactory()
        ui.app().setApplicationTitle(f"Two SelectionBox {backend.value} Test")

        dialog = factory.createPopupDialog()
        mainVbox = factory.createVBox(dialog)

        # HBox with two selection boxes
        hbox = factory.createHBox(mainVbox)        
        sel1 = factory.createSelectionBox(hbox, "First Box")
        sel2 = factory.createSelectionBox(hbox, "Second Box")

        # Populate items (use YItem so we can set initial selection)
        items1 = [
            yui.YItem("Apple"),
            yui.YItem("Banana"),
            yui.YItem("Cherry")
        ]
        items1[1].setSelected(True)

        items2 = [
            yui.YItem("Red"),
            yui.YItem("Green"),
            yui.YItem("Blue")
        ]
        items2[1].setSelected(True)

        sel1.addItems(items1)
        sel2.addItems(items2)

        # Label below the hbox that reports which box sent the event and its value
        label_box = factory.createVBox(mainVbox)
        infoLabel = factory.createLabel(label_box, "<no selection>")
        infoLabel.setStretchable(yui.YUIDimension.YD_HORIZ, True)

        # OK button to exit
        okButton = factory.createPushButton(label_box, "OK")

        # Initial display
        try:
            v1 = sel1.value() or (sel1.selectedItem().label() if sel1.selectedItem() else "<none>")
        except Exception:
            v1 = "<none>"
        try:
            v2 = sel2.value() or (sel2.selectedItem().label() if sel2.selectedItem() else "<none>")
        except Exception:
            v2 = "<none>"
        infoLabel.setText(f"Box1: {v1} | Box2: {v2}")

        # Event loop
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
                if wdg == okButton:
                    dialog.destroy()
                    break
                elif wdg == sel1 or wdg == sel2:
                    # Update label with which box and its value
                    try:
                        v1 = sel1.value() or (sel1.selectedItem().label() if sel1.selectedItem() else "<none>")
                    except Exception:
                        v1 = "<none>"
                    try:
                        v2 = sel2.value() or (sel2.selectedItem().label() if sel2.selectedItem() else "<none>")
                    except Exception:
                        v2 = "<none>"
                    who = "Box1" if wdg == sel1 else "Box2"
                    infoLabel.setText(f"Now({who}: {wdg.value()}) [Box1: {v1}] [Box2: {v2}]")

    except Exception as e:
        print(f"Error in test_two_selectionbox with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_two_selectionbox(sys.argv[1])
    else:
        test_two_selectionbox()
