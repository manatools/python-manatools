# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:

'''
ui dialog demo

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools
'''

import manatools.ui.basedialog as basedialog
import yui
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
    basedialog.BaseDialog.__init__(self, "Test dialog", "", basedialog.DialogType.POPUP, 80, 10)
    
  def UIlayout(self, layout):
    '''
    layout implementation called in base class to setup UI
    '''
    
    # Let's test a Menu widget
    menu = self.factory.createMenuButton(self.factory.createLeft(layout), "Test &menu")
    tm1 = yui.YMenuItem("menu item 1")
    tm2 = yui.YMenuItem("menu item 2")
    qm = yui.YMenuItem("&Quit")
    menu.addItem(tm1)
    menu.addItem(tm2)
    menu.addItem(qm)
    menu.rebuildMenuTree()
    sendObjOnEvent=True
    self.eventManager.addMenuEvent(tm1, self.onMenuItem, sendObjOnEvent)
    self.eventManager.addMenuEvent(tm2, self.onMenuItem, sendObjOnEvent)
    self.eventManager.addMenuEvent(qm, self.onQuitEvent, sendObjOnEvent)
    
    #let's test some buttons
    hbox = self.factory.createHBox(layout)
    self.pressButton = self.factory.createPushButton(hbox, "&Press")
    self.eventManager.addWidgetEvent(self.pressButton, self.onPressButton)

    #Let's enable a time out on events
    self.timeoutButton = self.factory.createPushButton(hbox, "&Test timeout")
    self.eventManager.addWidgetEvent(self.timeoutButton, self.onTimeOutButtonEvent)
    self.eventManager.addTimeOutEvent(self.onTimeOutEvent)

    # Let's test a quitbutton (same handle as Quit menu)
    self.quitButton = self.factory.createPushButton(layout, "&Quit")
    self.eventManager.addWidgetEvent(self.quitButton, self.onQuitEvent, sendObjOnEvent)
    
    # Let's test a cancel event
    self.eventManager.addCancelEvent(self.onCancelEvent)
    
  def onMenuItem(self, item):
      print ("Menu item <<", item.label(), ">>")
      
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
    if isinstance(obj, yui.YItem):
      print ("Quit menu pressed")
    else:
      print ("Quit button pressed")
    # BaseDialog needs to force to exit the handle event loop 
    self.ExitLoop()

if __name__ == '__main__':
      
  td = TestDialog()
  td.run()
  
  
