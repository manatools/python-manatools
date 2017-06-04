# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:

'''
EventManger class

License: GPLv3

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools
'''

import manatools.event as event
import manatools.eventmanager as eventManager

######################################################################
## 
## Demo test Events
## 
######################################################################


class TestEvents:
  def __init__(self):
    self.em = eventManager.EventManager()
    widget = "Button"
    self.em.addWidgetEvent(widget, self.onButton)
    widget = "Menu"
    self.em.addWidgetEvent(widget, self.onMenu)
    self.em.addWidgetEvent(widget, self.onMenu)
    print(self.em)

  def onButton(self) :
    print ("Button pressed")

  def onMenu(self, s) :
    print ("Menu [%s] pressed"%(s))

  def run(self):
    print("Widget events: %d"%(len(self.em._widgetEvent)))
    self.em.widgetEvent("Button")
    self.em.widgetEvent("Menu", "File")
    self.em.removeWidgetEvent("Menu", self.onMenu)
    print("Widget events: %d"%(len(self.em._widgetEvent)))
    self.em.widgetEvent("Menu", "Exit")
    self.em.widgetEvent("Button")
    self.em.removeWidgetEvent("Button", self.onButton)
    print("Widget events: %d"%(len(self.em._widgetEvent)))
    self.em.widgetEvent("Button")

if __name__ == '__main__':
  te = TestEvents()
  te.run()

