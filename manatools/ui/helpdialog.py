# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.ui.helpdialog contains all the HelpDialog class
that should be use into a manatools application

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.ui.helpdialog
'''
import webbrowser

import manatools.ui.basedialog as basedialog
import manatools.basehelpinfo as helpdata
import yui
import gettext
# https://pymotw.com/3/gettext/#module-localization
t = gettext.translation(
    'python-manatools',
    '/usr/share/locale',
    fallback=True,
)
_ = t.gettext
ngettext = t.ngettext

class HelpDialog(basedialog.BaseDialog):
  def __init__(self, info, title=_("Help dialog"), icon="", minWidth=80, minHeight=20):
    basedialog.BaseDialog.__init__(self, title, icon, basedialog.DialogType.POPUP, minWidth, minHeight)
    '''
    HelpDialog constructor
    @param title dialog title
    @param icon dialog icon
    @param minWidth > 0 mim width size, see libYui createMinSize
    @param minHeight > 0 mim height size, see libYui createMinSize
    '''
    if not isinstance(info, helpdata.HelpInfoBase):
      raise TypeError("info must be a HelpInfoBase instance")
    self.info = info

  def UIlayout(self, layout):
    '''
    layout implementation called in base class to setup UI
    '''
    # URL events are sent as YMenuEvent by libyui
    self.eventManager.addMenuEvent(None, self.onURLEvent, False)
    self.text = self.factory.createRichText(layout, "", False)
    self.text.setValue(self.info.home())
    align = self.factory.createRight(layout)
    self.quitButton = self.factory.createPushButton(align, _("&Quit"))
    self.eventManager.addWidgetEvent(self.quitButton, self.onQuitEvent)

  def onQuitEvent(self) :
    # BaseDialog needs to force to exit the handle event loop
    self.ExitLoop()

  def onURLEvent(self, mEvent):
    url = mEvent.id()
    if url:
      text = self.info.show(url)
      if text:
        self.text.setValue(text)
      else:
        print("onURLEvent: running webbrowser", url)
        webbrowser.open(url, 2)
