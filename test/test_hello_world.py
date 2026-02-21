#!/usr/bin/env python3

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_hello_world(backend_name=None):
    """Test simple dialog with hello world"""
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
        
        ui = YUI_ui()
        factory = ui.widgetFactory()
        dialog = factory.createMainDialog()

        vbox = factory.createVBox( dialog )
        factory.createLabel( vbox, "Hello, World!" )
        factory.createPushButton( vbox, "OK" )
        dialog.open()
        event = dialog.waitForEvent()
        dialog.destroy()

        
    except Exception as e:
        print(f"Error testing ComboBox with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_hello_world(sys.argv[1])
    else:
        test_hello_world()
