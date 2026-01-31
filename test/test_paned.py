# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
"""
Test script for YPaned using the YUI abstraction (inspired by test_frame.py).

- Horizontal paned: Tree widget + Table.
- Vertical paned: RichText + Table.
- Dialog includes a push button to quit.

No backend-specific fallback; if it fails, fix the widget implementation.
"""

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

def test_paned(backend_name=None):
    """Interactive test showcasing YDumbTab with three tabs and a ReplacePoint."""
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

        # Basic logging for diagnosis
        import logging
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

        ui = YUI_ui()
        factory = ui.widgetFactory()
        dialog = factory.createMainDialog()
        mainVbox = factory.createVBox( dialog )
        paned_h = factory.createPaned(mainVbox, yui.YUIDimension.YD_HORIZ)
        tree = factory.createTree(paned_h, "Test Tree")
        tree.setStretchable(yui.YUIDimension.YD_HORIZ, True)
        tree.setStretchable(yui.YUIDimension.YD_VERT, True)
        items = []
        for i in range(1, 6):
            itm = yui.YTreeItem(f"Item {i}", is_open=(i == 1))
            for j in range(1, 4):
                sub = yui.YTreeItem(f"SubItem {i}.{j}", parent=itm)
                for k in range(1, 3):
                    yui.YTreeItem(f"SubItem {i}.{j}.{k}", parent=sub)
            items.append(itm)
            tree.addItem(itm)
        header = yui.YTableHeader()
        header.addColumn('num.', alignment=yui.YAlignmentType.YAlignEnd)
        header.addColumn('document', alignment=yui.YAlignmentType.YAlignBegin)        
        table_h = factory.createTable(paned_h, header)
        table_h.setStretchable(yui.YUIDimension.YD_HORIZ, True)
        table_h.setStretchable(yui.YUIDimension.YD_VERT, True)
        items = []
        for i in range(1, 7):
            itm = yui.YTableItem(f"Row {i}")
            itm.addCell(str(i))
            itm.addCell(f"test_{i}")
            items.append(itm)
            table_h.addItem(itm)
        paned_v = factory.createPaned(mainVbox, yui.YUIDimension.YD_VERT)
        rich = factory.createRichText(
            paned_v,
            "<h2>RichText sample</h2><ul><li>Line 1</li><li>Line 2</li></ul>Visit: https://example.org",    
        )
        rich.setStretchable(yui.YUIDimension.YD_HORIZ, True)
        rich.setStretchable(yui.YUIDimension.YD_VERT, True)
        header = yui.YTableHeader()
        header.addColumn('num.', alignment=yui.YAlignmentType.YAlignEnd)
        header.addColumn('info', alignment=yui.YAlignmentType.YAlignBegin)
        header.addColumn('', checkBox=True, alignment=yui.YAlignmentType.YAlignCenter)
        table_v = factory.createTable(paned_v, header)
        table_v.setStretchable(yui.YUIDimension.YD_HORIZ, True)
        table_v.setStretchable(yui.YUIDimension.YD_VERT, True)
        items = []
        for i in range(1, 7):
            itm = yui.YTableItem(f"Row {i}")
            itm.addCell(str(i))
            itm.addCell(f"test {i}")
            # third column is checkbox column
            itm.addCell(False if i % 2 == 0 else True)
            items.append(itm)
            table_v.addItem(itm)
        btn_quit = factory.createPushButton(mainVbox, "Quit")
        
        #
        # Event loop
        #
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
                if wdg == btn_quit:
                    dialog.destroy()
                    break
                if wdg == tree:
                    sel = tree.selectedItem()
                    if sel:
                        root_logger.debug(f"Tree selection changed: {sel.label()}")
                elif wdg == table_h:
                    sel = table_h.selectedItem()
                    if sel:
                        root_logger.debug(f"Horizontal Table selection changed: {sel.label(0)} {sel.label(1)}")
                elif wdg == table_v:
                    sel = table_v.selectedItem()
                    if sel:
                        root_logger.debug(f"Vertical Table selection changed: {sel.label(0)} {sel.label(1)}")   
            
          else:
              print(f"Unhandled event type: {typ}")
    
    except Exception as e:
        print(f"Error testing Paned with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_paned(sys.argv[1])
    else:
        test_paned()