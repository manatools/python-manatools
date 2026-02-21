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
        root_logger.info("test_tree: program=%s backend=%s", os.path.basename(sys.argv[0]), getattr(backend, 'value', str(backend)))
                
        ui = YUI_ui()
        factory = ui.widgetFactory()
        title = ui.application().applicationTitle()
        ui.application().setApplicationTitle("Tree Widget Application")
        
        # Create dialog focused on ComboBox testing
        dialog = factory.createMainDialog()
        vbox = factory.createVBox(dialog)
        
        factory.createHeading(vbox, "Tree Test")
        factory.createLabel(vbox, f"Backend: {backend.value}")
        factory.createLabel(vbox, "Test selecting and displaying values")
        
        # Test ComboBox with initial selection
        factory.createLabel(vbox, "")
        hbox = factory.createHBox(vbox)
        tree = factory.createTree(hbox, "Select:")
        
        for i in range(5):            
            item = yui.YTreeItem(f"Item {i+1}", is_open=(i==0))
            for j in range(3):
                subitem = yui.YTreeItem(f"SubItem {i+1}.{j+1}", parent=item, selected=(True if i==1 and j == 2 else False))
                if i==1 and j == 1:
                    for k in range(2):
                        yui.YTreeItem(f"SubItem {i+1}.{j+1}.{k+1}", parent=subitem)

            tree.addItem(item)

        selected = factory.createLabel(vbox, "Selected:")
        hbox = factory.createHBox(vbox)
        ok_button = factory.createPushButton(hbox, "OK")
        cancel_button = factory.createPushButton(hbox, "Cancel")
        
        print("\nOpening ComboBox test dialog...")
       
        dialog.open()
        if tree.selectedItem() is not None:
           selected.setText(f"Selected: '{tree.selectedItem().label()}'")
        else:
           selected.setText(f"Selected: None")
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
                        if tree.selectedItem() is not None:
                            selected.setText(f"Selected: '{tree.selectedItem().label()}'")
                        else:
                            selected.setText(f"Selected: None")
                    elif reason == yui.YEventReason.Activated:
                        if tree.selectedItem() is not None:
                            selected.setText(f"Activated: '{tree.selectedItem().label()}'") 
                        else:
                            selected.setText(f"Activated: None")
                elif wdg == ok_button:
                    selected.setText(f"OK clicked.")
        
        # Show final result
        if tree.selectedItem() is not None:
            print(f"\nFinal Tree value: '{tree.selectedItem().label()}'")
        
    except Exception as e:
        print(f"Error testing Tree with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ui.application().setApplicationTitle(title)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_tree(sys.argv[1])
    else:
        test_tree()
