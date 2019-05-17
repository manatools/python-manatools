# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:

'''
ui help dialog demo

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools
'''

import manatools.ui.basedialog as basedialog
import yui
import time

######################################################################
## 
## Help Dialog demo
## 
######################################################################

class HelpInfoBase:
  def __init__(self):
    pass

  def show(self, info_to_show):
    '''
    super class must implement show to return the right string to show
    into dialog
    @param info_to_show: a kind of index of what to show, it depends on implementation
    '''
    raise NotImplementedError("show is not implemented")

  def home(self):
    '''
    super class must implement show to return the very first info to show
    into dialog, such as index for instance. Than index could be anchored and anchors passed
    to show() to display related content
    '''
    raise NotImplementedError("home is not implemented")

class HelpInfo(HelpInfoBase):
  def __init__(self):
    HelpInfoBase.__init__(self)
    index1 = '<b>%s</b>'%self._formatLink("Title 1", 'title1')
    index2 = '<b>%s</b>'%self._formatLink("Title 2", 'titleindex2')
    self.text = { 'home': "This text explain how to use manatools Help Dialog. <br><br>%s <br>%s"%(index1, index2),
                 'title1': '<h2>Title 1</h2>This is the title 1 really interesting context. <br> %s'%self._formatLink("Go to index", 'home'),
                 'titleindex2': '<h2>Title 1</h2>This is the title 2 interesting context. <br>%s'%self._formatLink("Go to index", 'home'),
      }

  def _formatLink(self, description, url) :
    '''
    @param description: Description to be shown as link
    @param url: to be reach when click on $description link
    returns href string to be published
    '''
    webref = '<a href="%s">%s</a>'%(url, description)
    return webref

  def show(self, info):
    '''
    implement show
    '''
    if info in self.text.keys():
      return self.text[info]

    return ""

  def home(self):
    '''
    implement home
    '''
    return self.text['home']


class HelpDialog(basedialog.BaseDialog):
  def __init__(self, info):
    basedialog.BaseDialog.__init__(self, "Help dialog", "", basedialog.DialogType.POPUP, 80, 10)
    #### TODO check instance of HelpInfoBase
    self.info = info
    
  def UIlayout(self, layout):
    '''
    layout implementation called in base class to setup UI
    '''
    
    # Let's test a Menu widget
    menu = self.factory.createMenuButton(self.factory.createLeft(layout), "Test &menu")
    qm = yui.YMenuItem("&Quit")
    menu.addItem(qm)
    menu.rebuildMenuTree()
    sendObjOnEvent=True
    self.eventManager.addMenuEvent(qm, self.onQuitEvent, sendObjOnEvent)
    # URL events are sent as YMenuEvent by libyui
    self.eventManager.addMenuEvent(None, self.onURLEvent, False)

    self.text = self.factory.createRichText(layout, "", False)
    self.text.setValue(self.info.home())

    #let's test some buttons
    align = self.factory.createRight(layout)

    # Let's test a quitbutton (same handle as Quit menu)
    self.quitButton = self.factory.createPushButton(align, "&Quit")
    self.eventManager.addWidgetEvent(self.quitButton, self.onQuitEvent, sendObjOnEvent)
    
    # Let's test a cancel event
    self.eventManager.addCancelEvent(self.onCancelEvent)
    
  def onCancelEvent(self) :
    print ("Got a cancel event")

  def onQuitEvent(self, obj) :
    if isinstance(obj, yui.YItem):
      print ("Quit menu pressed")
    else:
      print ("Quit button pressed")
    # BaseDialog needs to force to exit the handle event loop 
    self.ExitLoop()

  def onURLEvent(self, mEvent):
    print("onURLEvent")
    url = mEvent.id()
    if url:
      self.text.setValue(self.info.show(url))

if __name__ == '__main__':

  info = HelpInfo()
  td = HelpDialog(info)
  td.run()
  
  
