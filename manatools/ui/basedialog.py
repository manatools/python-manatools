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
    print(f"BaseDialog init title={title} icon={icon} dialogType={dialogType} minWidth={minWidth} minHeight={minHeight}")
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
    super class must implement this to draw the dialog layout
    @param layout: a YUI vertical box layout
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
    self.backupTitle = yui.YUI.app().applicationTitle()
    yui.YUI.app().setApplicationTitle(self._title)
    if self._icon:
      backupIcon = yui.YUI.app().applicationIcon()
      yui.YUI.app().setApplicationIcon(self._icon)

    self._setupUI()
    
    self._running = True
    self._handleEvents()

    #restore old application title
    yui.YUI.app().setApplicationTitle(self.backupTitle)
    if self._icon:
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
    
    self.dialog = self.factory.createPopupDialog() if self._dialogType == DialogType.POPUP else self.factory.createMainDialog()
    
    parent = self.dialog
    if self._minSize is not None:
       parent = self.factory.createMinSize(self.dialog, self._minSize['minWidth'], self._minSize['minHeight'])
    
    vbox = self.factory.createVBox(parent)
    self.UIlayout(vbox)

  #def pollEvent(self):
  #  '''
  #  perform yui pollEvent
  #  '''
  #  return self.dialog.pollEvent()

  def _handleEvents(self):
    '''
    manage dialog events
    '''
    while self._running == True:

      event = self.dialog.waitForEvent(self.timeout)
      if event is not None:
        eventType = event.eventType()

        rebuild_package_list = False
        group = None
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
          print(f"Unmanaged event type {eventType}")
      else:
        #TODO logging
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
