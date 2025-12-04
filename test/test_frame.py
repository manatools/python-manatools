#!/usr/bin/env python3

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_selectionbox(backend_name=None):
    """Test Frame widget specifically"""
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
        ui.application().setApplicationTitle("Test Frame")
        dialog = factory.createPopupDialog()
        mainVbox = factory.createVBox( dialog )
        hbox = factory.createHBox( mainVbox )
        frame = factory.createFrame( hbox , "Pasta Menu")
        selBox = factory.createSelectionBox( frame, "Choose your pasta" )

        selBox.addItem( "Spaghetti Carbonara" )
        selBox.addItem( "Penne Arrabbiata" )
        selBox.addItem( "Fettuccine" )
        selBox.addItem( "Lasagna" )
        selBox.addItem( "Ravioli" )
        selBox.addItem( "Trofie al pesto" ) # Ligurian specialty

        frame1 = factory.createFrame( hbox , "SelectionBox Options")
        vbox = factory.createVBox( frame1 )
        align = factory.createTop(vbox)
        notifyCheckBox = factory.createCheckBox( align, "Notify on change", selBox.notify() )
        notifyCheckBox.setStretchable( yui.YUIDimension.YD_HORIZ, True )
        multiSelectionCheckBox = factory.createCheckBox( vbox, "Multi-selection", selBox.multiSelection() )
        multiSelectionCheckBox.setStretchable( yui.YUIDimension.YD_HORIZ, True )
        align = factory.createBottom( vbox )
        disableSelectionBox = factory.createCheckBox( align, "disable selection box", not selBox.isEnabled() )
        disableSelectionBox.setStretchable( yui.YUIDimension.YD_HORIZ, True )
        disableValue = factory.createCheckBox( vbox, "disable value button", False )
        disableValue.setStretchable( yui.YUIDimension.YD_HORIZ, True )

        hbox = factory.createHBox( mainVbox )
        valueButton = factory.createPushButton( hbox, "Value" ) 
        disableValue.setValue(not valueButton.isEnabled())
        label = factory.createLabel(hbox, "SelectionBox") #factory.createOutputField( hbox, "<SelectionBox value unknown>" )
        label.setStretchable( yui.YUIDimension.YD_HORIZ, True )
        valueField  = factory.createLabel(hbox, "<SelectionBox value unknown>")
        valueField.setStretchable( yui.YUIDimension.YD_HORIZ, True ) # // allow stretching over entire dialog width

        #factory.createVSpacing( vbox, 0.3 )

        hbox = factory.createHBox( mainVbox )
        #factory.createLabel(hbox, "   ") # spacer
        leftAlignment = factory.createLeft( hbox )
        left = factory.createPushButton( leftAlignment, "Left" )
        rightAlignment = factory.createRight( hbox )
        closeButton    = factory.createPushButton( rightAlignment, "Close" )

        #
        # Event loop
        #
        #valueField.setText( "???" )
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
              elif wdg == left:
                valueField.setText(left.label())
              elif (wdg == valueButton):                
                if selBox.multiSelection():
                    labels = [item.label() for item in selBox.selectedItems()]
                    valueField.setText( ", ".join(labels) )
                else:
                    item = selBox.selectedItem()
                    valueField.setText( item.label() if item else "<none>" )
                ui.application().setApplicationTitle("Test App")       
              elif (wdg == notifyCheckBox):
                selBox.setNotify( notifyCheckBox.value() )          
              elif (wdg == multiSelectionCheckBox):   
                selBox.setMultiSelection( multiSelectionCheckBox.value() )
              elif (wdg == disableSelectionBox):   
                selBox.setEnabled( not disableSelectionBox.value() )
              elif (wdg == disableValue):   
                valueButton.setEnabled( not disableValue.value() )
              elif (wdg == selBox):		# selBox will only send events with setNotify() TODO
                if selBox.multiSelection():
                    labels = [item.label() for item in selBox.selectedItems()]
                    valueField.setText( ", ".join(labels) )
                else:
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




