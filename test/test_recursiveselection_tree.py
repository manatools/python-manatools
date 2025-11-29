#!/usr/bin/env python3

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_tree(backend_name=None):
    """Test ComboBox widget specifically"""
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
        
        # Create dialog focused on ComboBox testing
        dialog = factory.createMainDialog()
        vbox = factory.createVBox(dialog)
        
        factory.createHeading(vbox, "Tree Test")
        factory.createLabel(vbox, f"Backend: {backend.value}")
        factory.createLabel(vbox, "Test selecting and displaying values")
        
        # Test ComboBox with initial selection
        factory.createLabel(vbox, "")
        hbox = factory.createHBox(vbox)
        tree = factory.createTree(hbox, "Select:", multiselection=False, recursiveselection=True)
        
        for i in range(5):            
            item = yui.YTreeItem(f"Item {i+1}", is_open=(i==0))
            for j in range(3):
                subitem = yui.YTreeItem(f"SubItem {i+1}.{j+1}", parent=item) 
                if i==1 and j == 1:
                    for k in range(2):
                        yui.YTreeItem(f"SubItem {i+1}.{j+1}.{k+1}", parent=subitem)

            tree.addItem(item)

        selected = factory.createLabel(vbox, "")
        hbox = factory.createHBox(vbox)
        ok_button = factory.createPushButton(hbox, "OK")
        cancel_button = factory.createPushButton(hbox, "Cancel")
        
        print("\nOpening ComboBox test dialog...")
       
        while True:
           event = dialog.waitForEvent()
           typ = event.eventType()
           if typ == yui.YEventType.CancelEvent:
                dialog.destroy()
                break
           elif typ == yui.YEventType.WidgetEvent:
                wdg = event.widget() 
                reason = event.reason()
                if wdg == cancel_button:
                    dialog.destroy()
                    break
                elif wdg == tree:
                    if reason == yui.YEventReason.SelectionChanged:
                        if tree.hasMultiSelection():
                            labels = [item.label() for item in tree.selectedItems()]
                            selected.setText(f"Selected: {labels}")
                        elif tree.selectedItem() is not None:
                            selected.setText(f"Selected: '{tree.selectedItem().label()}'")
                        else:
                            selected.setText("Selected: None")
                    elif reason == yui.YEventReason.Activated:
                        if tree.selectedItem() is not None:
                            selected.setText(f"Activated: '{tree.selectedItem().label()}'") 
                elif wdg == ok_button:
                    selected.setText(f"OK clicked.")
        
        # Show final result
        print(f"\nFinal Tree value: '{tree.selectedItem().label()}'")
        
    except Exception as e:
        print(f"Error testing Tree with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_tree(sys.argv[1])
    else:
        test_tree()
