#!/usr/bin/env python3

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_selectionbox(backend_name=None):
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
       

###############
        dialog = factory.createPopupDialog()
        vbox = factory.createVBox( dialog )
        hbox = factory.createHBox( vbox )
        selBox = factory.createSelectionBox( vbox, "Menu" )

        selBox.addItem( "Pizza Margherita" )
        selBox.addItem( "Pizza Capricciosa" )
        selBox.addItem( "Pizza Funghi" )
        selBox.addItem( "Pizza Prosciutto" )
        selBox.addItem( "Pizza Quattro Stagioni" )
        selBox.addItem( "Calzone" )

        checkBox = factory.createCheckBox( hbox, "Notify on change", selBox.notify() )

        hbox = factory.createHBox( vbox )
        factory.createLabel(hbox, "SelectionBox") #factory.createOutputField( hbox, "<SelectionBox value unknown>" )
        valueField  = factory.createLabel(vbox, "<SelectionBox value unknown>")
        #valueField.setStretchable( yui.YD_HORIZ, True ) # // allow stretching over entire dialog width

        valueButton = factory.createPushButton( hbox, "Value" ) 
        #factory.createVSpacing( vbox, 0.3 )

        #rightAlignment = factory.createRight( vbox ) TODO
        closeButton    = factory.createPushButton( vbox, "Close" )

        #
        # Event loop
        #
        valueField.setText( "???" )
        while True:
          event = dialog.waitForEvent()
          if not event:
            print("Empty")
            next
          typ = event.eventType()
          if typ == yui.YEventType.CancelEvent:
                dialog.destroy()
                break
          elif typ == yui.YEventType.WidgetEvent:
              wdg = event.widget()          
              if wdg == closeButton:
                dialog.destroy()
                break
              elif (wdg == valueButton):
                item = selBox.selectedItem()
                valueField.setText( item.label() if item else "<none>" )   
              elif (wdg == checkBox):
                selBox.setNotify( checkBox.value() )             
              elif (wdg == selBox):		# selBox will only send events with setNotify() TODO
                valueField.setText(selBox.value())
        
    except Exception as e:
        print(f"Error testing ComboBox with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_selectionbox(sys.argv[1])
    else:
        test_selectionbox()




