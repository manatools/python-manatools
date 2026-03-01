# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
ManaTools is a generic launcher application that can run
internal or external modules, such as system configuration tools.

ManaTools is also a collection of configuration tools that allows
users to configure most of their system components in a very simple,
intuitive and attractive interface. It consists of some modules
that can be also run as autonomous applications.

Python-ManaTools is a python framework to write manatools application
written in python, this project started from perl manatools experience
and its aim is to give an easy and common interface to develop and add
new modules based on libYui. Every modules can be run using QT, Gtk or
ncurses interface.

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.ui.basedialog
'''

from ..aui import yui as yui

from enum import Enum
import logging

logger = logging.getLogger("manatools.ui.basedialog")

from .. import event as event
from .. import eventmanager as eventManager

class DialogType(Enum):
    MAIN  = 1
    POPUP = 2

class BaseDialog :
  """
  BaseDialog is the base class to build libyui dialogs
  Example of usage:

  class MyDialog(basedialog.BaseDialog):
    def __init__(self):
      basedialog.BaseDialog.__init__(self, "My beautiful dialog")
    
    def UIlayout(self, layout):
      self.quitButton = self.factory.createPushButton(layout, "&Quit")
      self.eventManager.addWidgetEvent(self.quitButton, self.onQuitEvent)
    
    def onQuitEvent(self) :
       print ("Quit button pressed")
       self.ExitLoop()

  if __name__ == '__main__':
    d = MyDialog()
    d.run()
  """

  def __init__(self, title, icon="", dialogType=DialogType.MAIN, minWidth=-1, minHeight=-1):
    '''
    BaseDialog constructor
    @param title dialog title
    @param icon dialog icon
    @param dialogType (DialogType.MAIN or DialogType.POPUP)
    @param minWidth > 0 min width size in pixels
    @param minHeight > 0 min height size in pixels
    '''
    logger.debug("BaseDialog init title=%s icon=%s dialogType=%s minWidth=%s minHeight=%s", title, icon, dialogType, minWidth, minHeight)
    self._dialogType = dialogType
    self._icon = icon
    self._title = title
    self._mgaFactory = None
    self._running = False
    self._eventManager = eventManager.EventManager()
    self._timeout = 0
    self._minSize = None
    if minWidth > 0 and minHeight > 0 :
      self._minSize = { 'minHeight' : minHeight, 'minWidth' : minWidth}

  @property 
  def running(self):
    '''
    return if the dialog is running
    '''
    return  self._running

  @property
  def timeout(self):
    '''
    time in millisec to wait before sending a timeout event, e.g. no other events have been received.
    A value <= 0 means no timeout (wait forever).
    '''
    return self._timeout

  @timeout.setter
  def timeout(self, value):
    '''
    time in millisec to wait before sending a timeout event, e.g. no other events have been received.
    A value <= 0 means no timeout (wait forever).
    '''
    self._timeout = value if value >= 0 else 0

  def UIlayout(self, layout):
    '''
    Implement this method in subclasses to build the dialog widget tree.

    @param layout  A VBox that is the content root of the dialog.  Append all
                   top-level widgets here.  When minWidth/minHeight were given
                   to BaseDialog.__init__() this VBox sits inside a MinSize
                   container that enforces the overall dialog minimum size.

    Per-column minimum widths
    -------------------------
    When the layout contains a ReplacePoint whose content changes at runtime,
    sibling columns can be squeezed.  Use protect_column_min_width() to wrap
    any column that must keep a guaranteed minimum width::

      hbox = self.factory.createHBox(layout)
      tree_col = self.createMinSize(hbox, 160, 1)  # Min width 160px, min height 1px to prevent collapse
      tree_col.setWeight(MUI.YUIDimension.YD_HORIZ, 25)
      self.tree = self.factory.createTree(tree_col, "")
      frame = self.factory.createFrame(hbox, "")
      frame.setWeight(MUI.YUIDimension.YD_HORIZ, 75)
      self.rp = self.factory.createReplacePoint(frame)
    '''
    raise NotImplementedError("UIlayout is not implemented")

  def doSomethingIntoLoop(self):
    '''
    super class should implement this to do something inside the
    event handler loop, just after the events have been managed
    '''
    pass

  def run(self):
    '''
    run the Dialog
    '''
    self._setupUI()
    
    self.backupTitle = yui.YUI.app().applicationTitle()
    yui.YUI.app().setApplicationTitle(self._title)
    backupIcon = None
    if self._icon:
      try:
        backupIcon = yui.YUI.app().applicationIcon()
      except Exception:
        pass
      yui.YUI.app().setApplicationIcon(self._icon)
    
    self._running = True
    self._handleEvents()

    #restore old application title
    yui.YUI.app().setApplicationTitle(self.backupTitle)
    if self._icon and backupIcon is not None:
      yui.YUI.app().setApplicationIcon(backupIcon)
    if self.dialog is not None:
      self.dialog.destroy()
      self.dialog = None

  @property
  def eventManager(self):
    '''
    return the event manager to add and remove wdiget, item and cancel events
    .. seealso:: manatools.eventmanager 
    '''
    return self._eventManager

  @property
  def factory(self):
    '''
    return yui widget factory
    '''
    return yui.YUI.widgetFactory()
  
  def _setupUI(self):
    '''
    Create the dialog window, build an optional overall MinSize container, and
    invoke UIlayout().

    Subclassing
    -----------
    Override UIlayout(layout) - do not override _setupUI unless necessary.
    The dialog is opened lazily on the first call to dialog.waitForEvent().
    '''
    self.dialog = self.factory.createPopupDialog() if self._dialogType == DialogType.POPUP else self.factory.createMainDialog()

    # If a minimum size is requested, wrap the layout inside a MinSize container.
    # IMPORTANT: MinSize is a single-child container -> add a VBox inside it and
    # pass that VBox to UIlayout so multiple children can be attached there.
    content_vbox = None
    if self._minSize is not None:
        min_container = self.factory.createMinSize(self.dialog, self._minSize['minWidth'], self._minSize['minHeight'])
        content_vbox = self.factory.createVBox(min_container)        
    else:
        content_vbox = self.factory.createVBox(self.dialog)
    layout_parent = content_vbox
    # Build the dialog layout using the chosen parent (MinSize->VBox or root VBox)
    self.UIlayout(layout_parent)

  def _handleEvents(self):
    '''
    manage dialog events
    '''
    while self._running == True:

      event = self.dialog.waitForEvent(self.timeout)
      if event is not None:
        eventType = event.eventType()
        #event type checking
        if (eventType == yui.YEventType.WidgetEvent) :
          # widget selected
          widget  = event.widget()
          self.eventManager.widgetEvent(widget, event)
        elif (eventType == yui.YEventType.MenuEvent) :
          ### MENU ###
          item = event.item()
          self.eventManager.menuEvent(item, event)
        elif (eventType == yui.YEventType.CancelEvent) :
          self.eventManager.cancelEvent()
          break
        elif (eventType == yui.YEventType.TimeoutEvent) :
          self.eventManager.timeoutEvent()
        else:
          logger.warning("Unmanaged event type %s", eventType)
      else:
        pass

      self.doSomethingIntoLoop()

  def ExitLoop(self):
    '''
    Force to exit the handle event loop, after next event managed
    If a handler wanted to make the application exit should run this.
    Note that Cancel event handler does not require to force the application to exit,
    a Quit button or menu handlers do instead.
    '''
    self._running = False
