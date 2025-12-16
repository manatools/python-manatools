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
        
        backend = YUI.backend()
        print(f"Using backend: {backend.value}")
        
        ui = YUI_ui()
        factory = ui.widgetFactory()
        ui.app().setApplicationTitle(f"SelectionBox {backend.value} Test")

        dialog = factory.createPopupDialog()
        vbox = factory.createVBox( dialog )
        # Radio buttons selector for menu category (use factory abstraction)
        radios_container = factory.createHBox(vbox)
        rb1 = factory.createRadioButton(radios_container, "First courses", True)
        rb2 = factory.createRadioButton(radios_container, "Second courses", False)
        rb3 = factory.createRadioButton(radios_container, "Desserts", False)

        selBox = factory.createSelectionBox( vbox, "Menu" )

        # Default: first courses
        selBox.addItem( "Spaghetti Carbonara" )
        selBox.addItem( "Penne Arrabbiata" )
        selBox.addItem( "Fettuccine" )
        selBox.addItem( "Lasagna" )
        selBox.addItem( "Ravioli" )
        selBox.addItem( "Trofie al pesto" ) # Ligurian specialty

        hbox = factory.createHBox( vbox )
        checkBox = factory.createCheckBox( hbox, "Notify on change", selBox.notify() )
        factory.createLabel(hbox, "SelectionBox") #factory.createOutputField( hbox, "<SelectionBox value unknown>" )
        valueField  = factory.createLabel(hbox, "<SelectionBox value unknown>")
        #valueField.setStretchable( yui.YD_HORIZ, True ) # // allow stretching over entire dialog width

        valueButton = factory.createPushButton( vbox, "Value" ) 
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
              elif wdg in (rb1, rb2, rb3):
                # Category changed: replace selection box items accordingly
                try:
                    selBox.deleteAllItems()
                except Exception:
                    pass
                try:
                    if wdg == rb1:
                        # First courses (default)
                        selBox.addItem( "Spaghetti Carbonara" )
                        selBox.addItem( "Penne Arrabbiata" )
                        selBox.addItem( "Fettuccine" )
                        selBox.addItem( "Lasagna" )
                        selBox.addItem( "Ravioli" )
                        selBox.addItem( "Trofie al pesto" )
                    elif wdg == rb2:
                        # Second courses: 4 meat, 2 vegan
                        selBox.addItem( "Beef Steak" )
                        selBox.addItem( "Roast Chicken" )
                        selBox.addItem( "Pork Chops" )
                        selBox.addItem( "Lamb Ribs" )
                        selBox.addItem( "Vegan Burger" )
                        selBox.addItem( "Grilled Tofu" )
                    elif wdg == rb3:
                        # Desserts: 3 typical American desserts
                        selBox.addItem( "Apple Pie" )
                        selBox.addItem( "Cheesecake" )
                        selBox.addItem( "Brownies" )
                except Exception:
                    pass
                # update display to first item
                try:
                    first = selBox.selectedItem()
                    valueField.setText(first.label() if first else "<none>")
                except Exception:
                    try:
                        valueField.setText("<none>")
                    except Exception:
                        pass
        
    except Exception as e:
        print(f"Error testing ComboBox with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_selectionbox(sys.argv[1])
    else:
        test_selectionbox()




