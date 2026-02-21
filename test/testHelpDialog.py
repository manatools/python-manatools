# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:

'''
ui help dialog demo

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools
'''

import os
import sys
import manatools.basehelpinfo as helpdata
import manatools.ui.helpdialog as helpdialog

import yui
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import logging

logger = logging.getLogger("manatools.test.helpdialog")

######################################################################
## 
## Help Dialog demo
## 
######################################################################



class HelpInfo(helpdata.HelpInfoBase):
  def __init__(self):
    helpdata.HelpInfoBase.__init__(self)
    # Configure file logger for this test: write DEBUG logs to '<testname>.log' in cwd
    try:
      log_name = os.path.splitext(os.path.basename(__file__))[0] + '.log'
      fh = logging.FileHandler(log_name, mode='w')
      fh.setLevel(logging.DEBUG)
      fh.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s: %(message)s'))
      self._logger = logging.getLogger()
      self._logger.setLevel(logging.DEBUG)
      existing = False
      for h in list(self._logger.handlers):
        try:
          if isinstance(h, logging.FileHandler) and os.path.abspath(getattr(h, 'baseFilename', '')) == os.path.abspath(log_name):
            existing = True
            break
        except Exception:
          pass
      if not existing:
        self._logger.addHandler(fh)
      print(f"Logging test output to: {os.path.abspath(log_name)}")
    except Exception as _e:
      print(f"Failed to configure file logger: {_e}")

    self._logger.debug("Creating HelpInfo contents")
    index1 = '<b>%s</b>'%self._formatLink("Title 1", 'title1')
    index2 = '<b>%s</b>'%self._formatLink("Title 2", 'titleindex2')
    index3 = '<b>%s</b>'%self._formatLink("Info", 'info')
    html = (
        "<h1>Heading 1</h1>"
        "<h2>Heading 2</h2>"
        "<h3>Heading 3</h3>"
        "<h4>Heading 4</h4>"
        "<h5>Heading 5</h5>"
        "<h6>Heading 6</h6>"
        "<br/>"
        "<h2>Welcome to <i>RichText</i></h2>"
        "<br/>"
        "<p>This is a paragraph with <b>bold</b>, <i>italic</i>, and <u>underlined</u> text.</p>"
        "<p>Click the <a href='https://github.com/manatools/'>Manatools</a> or <a href='home'>go home</a> link to emit an activation event.</p>"
        "<p>Colored text:</p>"
        "<ul><li><span foreground=\"red\"><a href='red'>Red element</a></span></li>"
        "<li><span foreground=\"green\"><a href='green'>Green element</a></span></li>"
        "<li><span foreground=\"purple\"><a href='purple'>Purple element</a></span></li></ul>"
        "<p>Lists:</p>"
        "<ul><li>Alpha</li><li>Beta</li><li>Gamma</li></ul>"
    )
    self.text = { 'home': "This text explain how to use manatools Help Dialog. <br><br>%s - %s <br> %s"%(index1, index2, index3),
                 'info': html,
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

  
  
