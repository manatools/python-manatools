# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:

'''
ui help dialog demo

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools
'''

import manatools.basehelpinfo as helpdata
import manatools.ui.helpdialog as helpdialog

import yui
import time

######################################################################
## 
## Help Dialog demo
## 
######################################################################



class HelpInfo(helpdata.HelpInfoBase):
  def __init__(self):
    helpdata.HelpInfoBase.__init__(self)
    index1 = '<b>%s</b>'%self._formatLink("Title 1", 'title1')
    index2 = '<b>%s</b>'%self._formatLink("Title 2", 'titleindex2')
    self.text = { 'home': "This text explain how to use manatools Help Dialog. <br><br>%s <br>%s"%(index1, index2),
                 'title1': '<h2>Title 1</h2>This is the title 1 really interesting context. <br> %s'%self._formatLink("Go to index", 'home'),
                 'titleindex2': '<h2>Title 2</h2>This is the title 2 interesting context. <br>%s'%self._formatLink("Go to index", 'home'),
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


if __name__ == '__main__':

  info = HelpInfo()
  td = helpdialog.HelpDialog(info)
  td.run()
  
  
