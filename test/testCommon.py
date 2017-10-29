# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:

'''
ui dialog demo

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools
'''

import manatools.ui.basedialog as basedialog
import manatools.ui.common as common
import manatools.version as manatools
import yui
import time
import gettext

######################################################################
## 
## Demo Dialog
## 
######################################################################


class TestDialog(basedialog.BaseDialog):
  def __init__(self):
    basedialog.BaseDialog.__init__(self, "Test dialog", "", basedialog.DialogType.POPUP, 80, 10)
    
  def UIlayout(self, layout):
    '''
    layout implementation called in base class to setup UI
    '''
    
    # Let's test a Menu widget
    hbox = self.factory.createHBox(layout)
    menu = self.factory.createMenuButton(self.factory.createLeft(hbox), "&File")
    qm = yui.YMenuItem("&Quit")
    menu.addItem(qm)
    menu.rebuildMenuTree()
    self.eventManager.addMenuEvent(qm, self.onQuitEvent)

    menu = self.factory.createMenuButton(self.factory.createRight(hbox), "&Help")
    about = yui.YMenuItem("&About")
    menu.addItem(about)
    menu.rebuildMenuTree()
    self.eventManager.addMenuEvent(about, self.onAbout)

    #let's test some buttons
    hbox = self.factory.createHBox(layout)
    self.pressButton = self.factory.createPushButton(hbox, "&Warning")
    self.eventManager.addWidgetEvent(self.pressButton, self.onPressWarning)

    # Let's test a quitbutton (same handle as Quit menu)
    self.quitButton = self.factory.createPushButton(layout, "&Quit")
    self.eventManager.addWidgetEvent(self.quitButton, self.onQuitEvent)
    
    # Let's test a cancel event
    self.eventManager.addCancelEvent(self.onCancelEvent)
    
  def onAbout(self):
      '''
      About menu call back
      '''
      yes = common.askYesOrNo({"title": "Choose About dialog mode", "text": "Do you want a tabbed About dialog? <br>Yes means Tabbed, No Classic", "richtext" : True, 'default_button': 1 })
      if yes:
        common.AboutDialog({ 'name' : "Test Tabbed About Dialog",
                    'dialog_mode' : common.AboutDialogMode.TABBED,
                    'version' : manatools.__project_version__,
                    'credits' :"Copyright (C) 2014-2017 Angelo Naselli",
                    'license' : 'GPLv2',
                    'authors' : 'Angelo Naselli &lt;anaselli@linux.it&gt;',
                    'information' : "Tabbed About dialog additional information",
                    'description' : "Project description here",
                    'size': {'column': 50, 'lines': 6},
                    })
      else :
         common.AboutDialog({ 'name' : "Test Classic About Dialog",
                    'dialog_mode' : common.AboutDialogMode.CLASSIC,
                    'version' : manatools.__project_version__,
                    'credits' :"Copyright (C) 2014-2017 Angelo Naselli",
                    'license' : 'GPLv2',
                    'authors' : 'Angelo Naselli &lt;anaselli@linux.it&gt;',
                    'information' : "Classic About dialog additional information",
                    'description' : "Project description here",
                    'size': {'column': 50, 'lines': 5},
                    })
   
  def onPressWarning(self) :
    '''
    Warning button call back
    '''
    print ('Button "Press" pressed')
    wd = common.warningMsgBox({"title" : "Warning Dialog", "text": "Warning button has been pressed!", "richtext" : True})

  def onCancelEvent(self) :
    print ("Got a cancel event")

  def onQuitEvent(self) :
    '''
    Quit button call back
    '''
    ok = common.askYesOrNo({"title": "Quit confirmation", "text": "Do you really want to quit?", "richtext" : True })
    print ("Quit button pressed")
    # BaseDialog needs to force to exit the handle event loop 
    if ok:
        self.ExitLoop()

if __name__ == '__main__':
      
  gettext.install('manatools', localedir='/usr/share/locale', names=('ngettext',))
  
  td = TestDialog()
  td.run()

  common.destroyUI()
  
  
