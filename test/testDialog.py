# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:

'''
ui dialog demo

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools
'''

import os
import sys
# Prefer using the local workspace package when running this test directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import manatools.ui.basedialog as basedialog
from manatools.aui import yui
import time

######################################################################
## 
## Demo Dialog
## 
######################################################################

def TimeFunction(func):
    """
    This decorator prints execution time
    """
    def newFunc(*args, **kwargs):
        t_start = time.time()
        rc = func(*args, **kwargs)
        t_end = time.time()
        name = func.__name__
        print("%d: %s took %.2f sec"%(t_start, name, t_end - t_start))
        return rc

    newFunc.__name__ = func.__name__
    newFunc.__doc__ = func.__doc__
    newFunc.__dict__.update(func.__dict__)
    return newFunc


class TestDialog(basedialog.BaseDialog):
  def __init__(self):
    basedialog.BaseDialog.__init__(self, "Test dialog", "", basedialog.DialogType.POPUP, 320, 200)
    
  def UIlayout(self, layout):
    '''
    layout implementation called in base class to setup UI
    '''
    
    # Menu bar (top-level menubar)
    menubar = self.factory.createMenuBar(layout)
    top_menu = menubar.addMenu("Test menu")
    tm1 = menubar.addItem(top_menu, "menu item 1")
    tm2 = menubar.addItem(top_menu, "menu item 2")
    qm = menubar.addItem(top_menu, "Quit")
    # Ensure event handlers receive the menu item object
    sendObjOnEvent = True
    self.eventManager.addMenuEvent(tm1, self.onMenuItem, sendObjOnEvent)
    self.eventManager.addMenuEvent(tm2, self.onMenuItem, sendObjOnEvent)
    self.eventManager.addMenuEvent(qm, self.onQuitEvent, sendObjOnEvent)
    
    #let's test some buttons
    hbox = self.factory.createHBox(layout)
    self.pressButton = self.factory.createPushButton(hbox, "Press")
    self.eventManager.addWidgetEvent(self.pressButton, self.onPressButton)

    #Let's enable a time out on events
    self.timeoutButton = self.factory.createPushButton(hbox, "Test timeout")
    self.eventManager.addWidgetEvent(self.timeoutButton, self.onTimeOutButtonEvent)
    self.eventManager.addTimeOutEvent(self.onTimeOutEvent)

    self.factory.createVStretch(layout)
    align = self.factory.createHVCenter(layout)
    # Let's test a quitbutton (same handle as Quit menu)
    self.quitButton = self.factory.createPushButton(align, "&Quit")
    self.eventManager.addWidgetEvent(self.quitButton, self.onQuitEvent, sendObjOnEvent)
    
    # Let's test a cancel event
    self.eventManager.addCancelEvent(self.onCancelEvent)
    
  def onMenuItem(self, item):
      try:
        print ("Menu item <<", item.label(), ">>")
      except Exception:
        print("Menu item activated")
      
  def onTimeOutButtonEvent(self):
    if self.timeout > 0 :
      self.timeout = 0
      print ("Timeout disabled")
    else :
      self.timeout = 5000
      print ("Timeout of 5 secs activated")
    
  @TimeFunction
  def onTimeOutEvent(self):
    print ("Timeout occurred")
    
  def onPressButton(self) :
    print ('Button "Press" pressed')
    td = TestDialog()
    td.run()

  def onCancelEvent(self) :
    print ("Got a cancel event")

  def onQuitEvent(self, obj) :
    # obj can be a menu item (YMenuItem) or a widget (button)
    try:
      if isinstance(obj, yui.YMenuItem):
        print ("Quit menu pressed")
      else:
        print ("Quit button pressed")
    except Exception:
      print ("Quit invoked")
    # BaseDialog needs to force to exit the handle event loop 
    self.ExitLoop()

if __name__ == '__main__':        
  if len(sys.argv) > 1:
    os.environ['YUI_BACKEND'] = sys.argv[1]

  td = TestDialog()
  td.run()
  
  
