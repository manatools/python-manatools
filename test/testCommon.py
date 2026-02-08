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
import time
import gettext

# Prefer using the local workspace package when running this test directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import manatools.ui.basedialog as basedialog
import manatools.ui.common as common
import manatools.version as manatools
from manatools.aui import yui
# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import logging

######################################################################
## 
## Demo Dialog
## 
######################################################################


class TestDialog(basedialog.BaseDialog):
  def __init__(self):
    basedialog.BaseDialog.__init__(self, "Test dialog", "", basedialog.DialogType.POPUP, 320, 200)
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

    self._tabbed_information = "Tabbed About dialog additional information"
    self._about_dialog_size = (320, 240)
    self._about_metadata = {
      'setApplicationName': "Test Dialog",
      'setVersion': manatools.__project_version__,
      'setAuthors': 'Angelo Naselli &lt;anaselli@linux.it&gt; <br/> Author 2 <br/> Author 3 <br/> Author 4 <br/> Author 5',
      'setDescription': "Manatools Test Dialog example",
      'setLicense': 'GPLv2',
      'setCredits': "Copyright (C) 2014-2026 Angelo Naselli",
      'setLogo': 'manatools',
      'setInformation': "Classic About dialog additional information",
    }
    self._apply_about_metadata()

  def _apply_about_metadata(self, **overrides):
    '''
    Push application metadata to the active YUI backend so AboutDialog
    retrieves consistent information regardless of the selected backend.
    '''
    payload = dict(self._about_metadata)
    for setter_name, value in overrides.items():
      if value is not None:
        payload[setter_name] = value

    try:
      app = yui.YUI.app()
    except Exception as exc:
      logging.getLogger(__name__).debug("Unable to reach YUI app: %s", exc)
      return

    for setter_name, value in payload.items():
      setter = getattr(app, setter_name, None)
      if not callable(setter):
        continue
      try:
        setter(value)
      except Exception as exc:
        logging.getLogger(__name__).debug("Failed to apply %s: %s", setter_name, exc)

    
  def UIlayout(self, layout):
    '''
    layout implementation called in base class to setup UI
    '''
    
    # Menu bar at the very top (attach directly to the main vertical layout)
    menubar = self.factory.createMenuBar(layout)
    file_menu = menubar.addMenu("&File")
    qm = menubar.addItem(file_menu, "&Quit")
    self.eventManager.addMenuEvent(qm, self.onQuitEvent)

    help_menu = menubar.addMenu("&Help")
    about = menubar.addItem(help_menu, "&About")
    self.eventManager.addMenuEvent(about, self.onAbout)

    # Let's test some buttons (inside the content area)
    self.factory.createVStretch(layout)
    hbox = self.factory.createHBox(layout)    
    self.warnButton = self.factory.createPushButton(hbox, "&Warning")
    self.eventManager.addWidgetEvent(self.warnButton, self.onPressWarning)
    self.infoButton = self.factory.createPushButton(hbox, "&Information")
    self.eventManager.addWidgetEvent(self.infoButton, self.onPressInformation)
    self.OkCancelButton = self.factory.createPushButton(hbox, "&Ok/Cancel Dialog")
    self.eventManager.addWidgetEvent(self.OkCancelButton, self.onPressOkCancel)

    self.factory.createVStretch(layout)
    hbox = self.factory.createHBox(layout)
    align = self.factory.createRight(hbox)
    # Let's test a quitbutton (same handle as Quit menu)
    self.quitButton = self.factory.createPushButton(align, "&Quit")
    self.eventManager.addWidgetEvent(self.quitButton, self.onQuitEvent)
    
    # Let's test a cancel event
    self.eventManager.addCancelEvent(self.onCancelEvent)
    
  def onAbout(self):
      '''
      About menu call back
      '''
      yes = common.askYesOrNo({"title": "Choose About dialog mode", "text": "Do you want a tabbed About dialog? <br>Yes means Tabbed, No Classic", "richtext" : True, 'default_button': 1 })
      selected_mode = common.AboutDialogMode.TABBED if yes else common.AboutDialogMode.CLASSIC
      info_text = self._tabbed_information if yes else self._about_metadata.get('setInformation', "")
      self._apply_about_metadata(setInformation=info_text)
      common.AboutDialog(dialog_mode=selected_mode, size=self._about_dialog_size)
   
  def onPressWarning(self) :
    '''
    Warning button call back
    '''
    print ('Button "Warning" pressed')
    wd = common.warningMsgBox({"title" : "Warning Dialog", "text": "<b>Warning</b> button has been pressed!", "richtext" : True})

  def onPressInformation(self) :
    '''
    Information button call back
    '''
    print ('Button "Information" pressed')
    id = common.infoMsgBox({"title" : "Information Dialog", "text": "<b>Information</b> button has been pressed!", "richtext" : True})

  def onPressOkCancel(self) :
    '''
    Ok/Cancel button call back
    '''
    print ('Button "Ok/Cancel Dialog" pressed')
    ok = common.askOkCancel({"title": "Ok/Cancel Dialog", "text": "To proceed, click <b>OK</b> or <b>Cancel</b> to skip.", "richtext" : True })
    print ("User selected: %s" % ("OK" if ok else "Cancel"))

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
  # Allow selecting backend via argv: e.g. `python3 test/testCommon.py gtk`
  if len(sys.argv) > 1:
    backend = sys.argv[1].lower()
    os.environ['YUI_BACKEND'] = backend

  gettext.install('manatools', localedir='/usr/share/locale', names=('ngettext',))

  td = TestDialog()
  td.run()

  common.destroyUI()


