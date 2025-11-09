#!/usr/bin/env python3

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_combobox(backend_name=None):
    """Test ComboBox widget specifically"""
    if backend_name:
        print(f"Setting backend to: {backend_name}")
        os.environ['YUI_BACKEND'] = backend_name
    else:
        print("Using auto-detection")
    
    try:
        from manatools.aui.yui import YUI, YUI_ui
        
        # Force re-detection
        YUI._instance = None
        YUI._backend = None
        
        backend = YUI.backend()
        print(f"Using backend: {backend.value}")
        
        if backend.value == 'ncurses':
            print("\nNCurses ComboBox Instructions:")
            print("1. Use TAB to navigate to ComboBox")
            print("2. Press SPACE to expand dropdown")
            print("3. Use UP/DOWN arrows to navigate")
            print("4. Press ENTER to select")
            print("5. Selected value should be displayed")
            print("6. Press F10 or Q to quit")
        
        ui = YUI_ui()
        factory = ui.widgetFactory()
        
        # Create dialog focused on ComboBox testing
        dialog = factory.createMainDialog()
        vbox = factory.createVBox(dialog)
        
        factory.createHeading(vbox, "ComboBox Test")
        factory.createLabel(vbox, f"Backend: {backend.value}")
        factory.createLabel(vbox, "Test selecting and displaying values")
        
        # Test ComboBox with initial selection
        factory.createLabel(vbox, "")
        hbox = factory.createHBox(vbox)
        combo = factory.createComboBox(hbox, "Choose fruit:", False)
        combo.addItem("Apple")
        combo.addItem("Banana") 
        combo.addItem("Orange")
        combo.addItem("Grape")
        combo.addItem("Mango")
        
        # Set initial value to test display
        combo.setValue("Banana")
        
        factory.createLabel(hbox, " - ")        
        combo = factory.createComboBox(hbox, "Choose option:", False)
        combo.addItem("Option 1")
        combo.addItem("Option 2") 
        combo.addItem("Option 3")

        # Simple buttons
        factory.createLabel(vbox, "")
        hbox = factory.createHBox(vbox)
        ok_button = factory.createPushButton(hbox, "OK")
        cancel_button = factory.createPushButton(hbox, "Cancel")
        
        print("\nOpening ComboBox test dialog...")
        
        # Store reference to check final value
        dialog._test_combo = combo
        
        # Open dialog
        dialog.open()
        
        # Show final result
        print(f"\nFinal ComboBox value: '{dialog._test_combo.value()}'")
        
    except Exception as e:
        print(f"Error testing ComboBox with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_combobox(sys.argv[1])
    else:
        test_combobox()
