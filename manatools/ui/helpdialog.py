# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.ui.helpdialog contains all the HelpDialog class
that should be use into a manatools application

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.ui.helpdialog
'''
import logging
import webbrowser

from . import basedialog as basedialog
from .. import basehelpinfo as helpdata
from ..aui import yui as yui
import gettext
# https://pymotw.com/3/gettext/#module-localization
t = gettext.translation(
    'python-manatools',
    '/usr/share/locale',
    fallback=True,
)
_ = t.gettext
ngettext = t.ngettext

logger = logging.getLogger("manatools.ui.helpdialog")

class HelpDialog(basedialog.BaseDialog):
  """Simple rich-text help browser dialog with internal navigation."""
  def __init__(self, info, title=_("Help dialog"), icon="", minWidth=320, minHeight=200):
    self._minWidthHint = self._normalize_dimension(minWidth)
    self._minHeightHint = self._normalize_dimension(minHeight)
    basedialog.BaseDialog.__init__(self, title, icon, basedialog.DialogType.POPUP, -1, -1)
    '''
    HelpDialog constructor
    @param title dialog title
    @param icon dialog icon
    @param minWidth > 0 mim width size in pixels
    @param minHeight > 0 mim height size in pixels
    '''
    if not isinstance(info, helpdata.HelpInfoBase):
      raise TypeError("info must be a HelpInfoBase instance")
    self.info = info
    logger.debug(
      "HelpDialog initialized title=%s icon=%s minWidth=%s minHeight=%s",
      title,
      icon,
      self._minWidthHint,
      self._minHeightHint,
    )

  @staticmethod
  def _normalize_dimension(value):
    """Return positive integer dimension or 0 if invalid."""
    try:
      dimension = int(value)
    except (TypeError, ValueError):
      return 0
    return dimension if dimension > 0 else 0

  def UIlayout(self, layout):
    '''
    layout implementation called in base class to setup UI
    '''
    # URL events may be sent as MenuEvent by backends that support it
    self.eventManager.addMenuEvent(None, self.onURLEvent, False)
    content_parent = layout
    if self._minWidthHint and self._minHeightHint:
      try:
        min_container = self.factory.createMinSize(layout, self._minWidthHint, self._minHeightHint)
        content_parent = self.factory.createVBox(min_container)
        logger.debug(
          "Applied min-size container (%s x %s) to HelpDialog",
          self._minWidthHint,
          self._minHeightHint,
        )
      except Exception as exc:
        content_parent = layout
        logger.debug("Unable to apply min-size hint: %s", exc)    
    self.text = self.factory.createRichText(content_parent, "", False)
    self.text.setStretchable(yui.YUIDimension.YD_HORIZ, True)
    self.text.setStretchable(yui.YUIDimension.YD_VERT, True)
    self.text.setValue(self.info.home())
    logger.debug("Initial help content loaded")

    button_row = self.factory.createHBox(content_parent)
    self.factory.createHStretch(button_row)
    self.quitButton = self.factory.createPushButton(button_row, _("Quit"))
    self.eventManager.addWidgetEvent(self.quitButton, self.onQuitEvent)
    logger.debug("Quit button registered")

  def onQuitEvent(self) :
    """Handle Quit button activation and terminate the dialog loop."""
    # BaseDialog needs to force to exit the handle event loop
    logger.debug("Quit event triggered")
    self.ExitLoop()

  def onURLEvent(self, mEvent):
    """Handle rich text URL activations and navigate or open links."""
    url = mEvent.id()
    if url:
      text = self.info.show(url)
      if text:
        self.text.setValue(text)
        logger.debug("Help content switched to %s", url)
      else:
        logger.debug("Opening external URL %s", url)
        try:
          webbrowser.open(url, 2)
        except Exception as exc:
          logger.error("Failed to open URL %s: %s", url, exc)
