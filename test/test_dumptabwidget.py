#!/usr/bin/env python3

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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
                factory.createLabel(box, "Use TAB/Shift+TAB to navigate")
                rp.showChild()
            elif index == 1:
                box = factory.createVBox(rp)
                factory.createLabel(box, "Notes:")
                text = "This is a simple multi-tab demo.\nSwitch tabs with LEFT/RIGHT (or UI specific).\nThe content below changes per tab."
                try:
                    factory.createRichText(box, text, plainTextMode=True)
                except Exception:
                    factory.createLabel(box, text)
                rp.showChild()
            else:
                box = factory.createVBox(rp)
                factory.createLabel(box, "Choose an action:")
                h = factory.createHBox(box)
                factory.createPushButton(h, "OK")
                factory.createPushButton(h, "Cancel")
                rp.showChild()

        # Initial content for the first tab
        render_content(0)

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
