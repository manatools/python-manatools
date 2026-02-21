#!/usr/bin/env python3

import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
  log_name = os.path.splitext(os.path.basename(__file__))[0] + '.log'
  fh = logging.FileHandler(log_name, mode='w')
  fh.setLevel(logging.DEBUG)
  fh.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s: %(message)s'))
  root_logger = logging.getLogger()
  root_logger.setLevel(logging.DEBUG)
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

def test_dumbtab(backend_name=None):
    """Interactive test showcasing YDumbTab with three tabs and a ReplacePoint."""
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

        # Basic logging for diagnosis
        import logging
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

        ui = YUI_ui()
        factory = ui.widgetFactory()
        dialog = factory.createMainDialog()

        vbox = factory.createVBox(dialog)
        factory.createHeading(vbox, "YDumbTab Test")
        factory.createLabel(vbox, f"Backend: {backend.value}")

        # Create DumbTab and items
        dumbtab = factory.createDumbTab(vbox)
        tabs = ["Options", "Notes", "Actions"]
        # Add items (select the first by default)
        it0 = yui.YItem(tabs[0], selected=True)
        it1 = yui.YItem(tabs[1])
        it2 = yui.YItem(tabs[2])
        dumbtab.addItem(it0)
        dumbtab.addItem(it1)
        dumbtab.addItem(it2)

        # Content area: ReplacePoint as the single child
        rp = factory.createReplacePoint(dumbtab)
        print("ReplacePoint created:", rp.widgetClass())

        # Helper to render content of the active tab
        def render_content(index: int):
            # Clear previous content
            try:
                rp.deleteChildren()
            except Exception:
                pass
            # Build new content depending on selected tab
            if index == 0:
                box = factory.createVBox(rp)
                factory.createLabel(box, "Enable the option below:")
                factory.createCheckBox(box, "Enable feature", is_checked=True)
                factory.createLabel(box, "Use this feature to blah blah...")
                rp.showChild()
                print("Rendered tab 0: Options")
            elif index == 1:
                box = factory.createVBox(rp)
                factory.createLabel(box, "Notes:")
                text = "This is a simple multi-tab demo.\nSwitch between tabs.\nThe content below changes per tab."
                minsize = factory.createMinSize(box, 320, 200)
                rt = factory.createRichText(minsize, text, plainTextMode=True)
                rt.setStretchable(yui.YUIDimension.YD_VERT, True)
                rt.setStretchable(yui.YUIDimension.YD_HORIZ, True)
                rp.showChild()
                print("Rendered tab 1: Notes")
            else:
                box = factory.createVBox(rp)
                factory.createLabel(box, "Choose an action:")
                h = factory.createHBox(box)
                factory.createPushButton(h, "OK")
                factory.createPushButton(h, "Cancel")
                rp.showChild()
                print("Rendered tab 2: Actions")

        # Initial content for the first tab
        render_content(0)
        print("Initial content rendered for tab 0.")

        # Close button
        close_row = factory.createHBox(vbox)
        close_btn = factory.createPushButton(close_row, "Close")

        print("\nOpening YDumbTab test dialog...")

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
                if wdg == dumbtab and reason == yui.YEventReason.Activated:
                    sel = dumbtab.selectedItem()
                    if sel is not None:
                        try:
                            idx = tabs.index(sel.label())
                        except Exception:
                            idx = 0
                        print("Tab Activated:", sel.label(), "index=", idx)
                        render_content(idx)

    except Exception as e:
        print(f"Error testing YDumbTab with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_dumbtab(sys.argv[1])
    else:
        test_dumbtab()
