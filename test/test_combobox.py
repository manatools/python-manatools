#!/usr/bin/env python3

import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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

def test_combobox(backend_name=None):
    """Test ComboBox widget specifically"""
    if backend_name:
        print(f"Setting backend to: {backend_name}")
        os.environ['YUI_BACKEND'] = backend_name
    else:
        print("Using auto-detection")
    
    try:
        #from manatools.aui.yui import YUI, YUI_ui 
        #import manatools.aui.yui_common as yui
        import manatools.aui.yui as MUI
        
        backend = MUI.YUI.backend()
        print(f"Using backend: {backend.value}")
        logger = logging.getLogger("test.test_combobox")
        logger.info(f"Testing ComboBox with backend: {backend.value}")
        
        if backend.value == 'ncurses':
            print("\nNCurses ComboBox Instructions:")
            print("1. Use TAB to navigate to ComboBox")
            print("2. Press SPACE to expand dropdown")
            print("3. Use UP/DOWN arrows to navigate")
            print("4. Press ENTER to select")
            print("5. Selected value should be displayed")
            print("6. Press F10 or Q to quit")
        
        ui = MUI.YUI_ui()
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
        label1 = "Select a fruit:"
        combo = factory.createComboBox(hbox, label1, False)
        fruits = [
            MUI.YItem("Apple"), MUI.YItem("Banana"), MUI.YItem("Orange", selected=True), MUI.YItem("Grape"), MUI.YItem("Mango")]
        combo.addItems(fruits)
                
        # Set initial value to test display
        combo.setValue("Banana")
        
        factory.createLabel(hbox, " - ")
        label2 = "Select an option:"
        combo1 = factory.createComboBox(hbox, label2, False)
        options = [
                MUI.YItem("Option 1"), MUI.YItem("Option 2", selected=True, icon_name="dialog-warning"), MUI.YItem("Option 3"), MUI.YItem("Option 4")]
        combo1.addItems(options)
        
        labels = [label1, label2]
        combo_items = [fruits, options]
        first_combo_info = 0
        # Simple buttons
        selected = factory.createLabel(vbox, "")
        hbox = factory.createHBox(vbox)
        swap_button = factory.createPushButton(hbox, "Swap ComboBoxes")
        cancel_button = factory.createPushButton(hbox, "Cancel")
        
        print("\nOpening ComboBox test dialog...")
       
        while True:
           event = dialog.waitForEvent()
           typ = event.eventType()
           if typ == MUI.YEventType.CancelEvent:
                dialog.destroy()
                break
           elif typ == MUI.YEventType.WidgetEvent:
                wdg = event.widget() 
                if wdg == cancel_button:
                    dialog.destroy()
                    break
                elif wdg == combo:
                    selected.setText(f"Selected: '{combo.value()}'")
                    for it in combo._items:
                        if it.selected():
                            logger.debug(f" - Item: '{it.label()}' Selected: {it.selected()} Icon: {it.iconName()}")
                elif wdg == combo1:
                    selected.setText(f"Selected: '{combo1.value()}'")
                    for it in combo1._items:
                        if it.selected():
                            logger.debug(f" - Item: '{it.label()}' Selected: {it.selected()} Icon: {it.iconName()}")

                elif wdg == swap_button:
                    selected.setText(f"Swap clicked.")
                    # Swap combo boxes
                    old = first_combo_info
                    first_combo_info = (first_combo_info + 1) % 2
                    combo.deleteAllItems()
                    combo1.deleteAllItems()
                    combo.setLabel(labels[first_combo_info])
                    combo.addItems(combo_items[first_combo_info])                    
                    combo1.setLabel(labels[(first_combo_info + 1) % 2])
                    combo1.addItems(combo_items[old])
        
        # Show final result
        print(f"\nFinal ComboBox value: '{combo.value()}' {combo1.value()}")
        
    except Exception as e:
        print(f"Error testing ComboBox with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_combobox(sys.argv[1])
    else:
        test_combobox()
