#!/usr/bin/env python3

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_Alignment(backend_name=None):
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

        vbox = factory.createVBox( dialog )
        factory.createLabel(vbox, "Testing aligment Left and Right into HBox")
        hbox = factory.createHBox( vbox )
        leftAlignment = factory.createLeft( hbox )
        left = factory.createPushButton( leftAlignment, "Left" )
        rightAlignment = factory.createRight( hbox )
        factory.createPushButton( rightAlignment, "Right" )

        hbox = factory.createHBox( vbox )
        rightAlignment = factory.createRight( hbox )
        btn = factory.createPushButton( rightAlignment, ">Right<" )
        btn.setStretchable( yui.YUIDimension.YD_HORIZ, True )

        factory.createLabel(vbox, "Testing aligment Top and Bottom into HBox")
        hbox = factory.createHBox( vbox )
        topAlignment = factory.createTop( hbox )
        factory.createPushButton( topAlignment, "Top" )
        factory.createLabel(hbox, "separator")
        bottomAlignment = factory.createBottom( hbox )
        factory.createPushButton( bottomAlignment, "Bottom" )

        factory.createLabel(vbox, "Testing aligment HCenter into HBox")
        hbox = factory.createHBox( vbox )
        align = factory.createHCenter( hbox )
        factory.createPushButton( align, "HCenter" )

        factory.createLabel(vbox, "Testing aligment VCenter into HBox")
        hbox = factory.createHBox( vbox )
        align = factory.createVCenter( hbox )
        factory.createPushButton( align, "VCenter" )

        factory.createLabel(vbox, "Testing aligment HVCenter into HBox")
        hbox = factory.createHBox( vbox )
        align = factory.createVCenter( hbox )
        factory.createPushButton( align, "HVCenter" )

        factory.createPushButton( vbox, "OK" )
        dialog.open()
        event = dialog.waitForEvent()
        dialog.destroy()

        
    except Exception as e:
        print(f"Error testing Alignment with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_Alignment(sys.argv[1])
    else:
        test_Alignment()
