#!/usr/bin/env python3

import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_backend(backend_name=None):
    """Test a specific backend"""
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
        
        # Create dialog
        dialog = factory.createMainDialog()
        vbox = factory.createVBox(dialog)
        
        # Add widgets - SAME LAYOUT FOR ALL BACKENDS
        factory.createHeading(vbox, f"manatools AUI {backend.value.upper()} Test")
        factory.createLabel(vbox, f"Backend: {backend.value}")
        
        if backend.value == 'ncurses':
            factory.createLabel(vbox, "ComboBox Test: Use SPACE to expand")
            factory.createLabel(vbox, "Then use ARROWS and ENTER to select")
        
        # Input fields
        input_field = factory.createInputField(vbox, "Username:")
        
        # ComboBox - NEW WIDGET
        combo = factory.createComboBox(vbox, "Select option:", False)
        combo.addItem("Option 1")
        combo.addItem("Option 2") 
        combo.addItem("Option 3")
        combo.addItem("Option 4")
        combo.addItem("Option 5")
        combo.addItem("Option 6")
        
        # Checkboxes
        checkbox = factory.createCheckBox(vbox, "Enable features")
        
        # Buttons
        selected = factory.createLabel(vbox, "")
        hbox = factory.createHBox(vbox)
        ok_button = factory.createPushButton(hbox, "OK")
        cancel_button = factory.createPushButton(hbox, "Cancel")
        
        print("Opening dialog...")
        
        while True:
           event = dialog.waitForEvent()
           typ = event.eventType()
           if typ == yui.YEventType.CancelEvent:
                dialog.destroy()
                break
           elif typ == yui.YEventType.WidgetEvent:
                wdg = event.widget() 
                if wdg == cancel_button:
                    dialog.destroy()
                    break
                elif wdg == combo:
                    selected.setText(f"Selected: '{combo.value()}'")                
                elif wdg == ok_button:
                    selected.setText(f"OK clicked. - {input_field.value()}")
                elif wdg == checkbox:
                    selected.setText(f"{checkbox.label()} - {checkbox.value()}")
        
        # Show results after dialog closes
        print(f"Dialog closed.")
        
    except Exception as e:
        print(f"Error with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()

def test_all_backends():
    """Test all available backends"""
    backends_to_test = []
    
    # Check which backends are available
    try:
        import PyQt5.QtWidgets
        backends_to_test.append('qt')
        print("✓ Qt backend available")
    except ImportError:
        print("✗ Qt backend not available")
    
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
        backends_to_test.append('gtk')
        print("✓ GTK backend available")
    except (ImportError, ValueError) as e:
        print(f"✗ GTK backend not available: {e}")
    
    try:
        import curses
        backends_to_test.append('ncurses')
        print("✓ NCurses backend available")
    except ImportError as e:
        print(f"✗ NCurses backend not available: {e}")
    
    print(f"\nAvailable backends: {backends_to_test}")
    
    for backend in backends_to_test:
        print(f"\n{'='*60}")
        print(f"Testing {backend.upper()} backend")
        print(f"{'='*60}")
        
        if backend == 'ncurses':
            print("\nNCurses ComboBox: Use SPACE to expand, arrows to navigate, ENTER to select")
            input("Press Enter to start...")
        
        test_backend(backend)
        
        if backend != 'ncurses' and backends_to_test.index(backend) < len(backends_to_test) - 1:
            input("Press Enter to test next backend...")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_backend(sys.argv[1])
    else:
        test_all_backends()
