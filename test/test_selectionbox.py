#!/usr/bin/env python3

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import logging

# Configure file logger for this test: write DEBUG logs to '<testname>.log' in cwd
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

def test_selectionbox(backend_name=None):
    """Test Selection Box widget specifically"""
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
        #ui.application().setIconBasePath("PATH_TO_TEST")

###############
        ui.application().setApplicationIcon("dnfdragora")
        dialog = factory.createPopupDialog()
        mainVbox = factory.createVBox( dialog )
        hbox = factory.createHBox( mainVbox )
        selBox = factory.createSelectionBox( hbox, "Choose your pasta" )
        selBox.addItem( "Spaghetti Carbonara" )
        selBox.addItem( "Penne Arrabbiata" )
        selBox.addItem( "Fettuccine" )
        selBox.addItem( "Lasagna" )
        selBox.addItem( "Ravioli" )
        selBox.addItem( "Trofie al pesto" ) # Ligurian specialty

        #selBox.setMultiSelection(True)

        vbox = factory.createVBox( hbox )
        notifyCheckBox = factory.createCheckBox( vbox, "Notify on change", selBox.notify() )
        notifyCheckBox.setStretchable( yui.YUIDimension.YD_HORIZ, True )
        multiSelectionCheckBox = factory.createCheckBox( vbox, "Multi-selection", selBox.multiSelection() )
        multiSelectionCheckBox.setStretchable( yui.YUIDimension.YD_HORIZ, True )
        disableSelectionBox = factory.createCheckBox( vbox, "disable selection box", not selBox.isEnabled() )
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
        if selBox.multiSelection():
           labels = [item.label() for item in selBox.selectedItems()]
           valueField.setText( ", ".join(labels) )
        else:
           item = selBox.selectedItem()
           valueField.setText( item.label() if item else "<none>" )


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




