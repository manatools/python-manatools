# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
EventManger class

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools
'''

import manatools.event as event

class EventManager:
    def __init__(self):
      '''
      EventManager manages 4 kind of YUI events:
      widget, menu, timeout and cancel
      '''
      self._widgetEvent = event.Event()
      self._menuEvent = event.Event()
      self._timeoutEvent = event.Event()
      self._cancelEvent = event.Event()

    def addTimeOutEvent(self, func):
      '''
      Add new TimeOut event handler function.
      Event handler function must be defined like func(owner, earg).
      '''
      ev = event.EventHandlerInfo("__timeout__", func)
      self._timeoutEvent += ev
    
    def removeTimeOutEvent(self, func):
      '''
      Add new TimeOut event handler function.
      Event handler function must be defined like func(owner, earg).
      '''
      ev = event.EventHandlerInfo("__timeout__", func)
      self._timeoutEvent -= ev

    def addCancelEvent(self, func):
      '''
      Add new Cancel event handler function.
      Event handler function must be defined like func(owner, earg).
      '''
      ev = event.EventHandlerInfo("__cancel__", func)
      self._cancelEvent += ev
    
    def removeCancelEvent(self, func):
      '''
      Add new Cancel event handler function.
      Event handler function must be defined like func(owner, earg).
      '''
      ev = event.EventHandlerInfo("__cancel__", func)
      self._cancelEvent -= ev
    
    def addWidgetEvent(self, widget, func, sendWidget=False):
      '''
      Add new Widget event handler function.
      Event handler function must be defined like func(owner, earg).
      If sendWidget is True func must be defined as func(owner, widget, earg)
      and involved widget is passed to handler
      '''
      ev = event.EventHandlerInfo(widget, func, sendWidget)
      self._widgetEvent += ev
    
    def removeWidgetEvent(self, widget, func=None):
      '''
      Add new Widget event handler function.
      Event handler function must be defined like func(owner, earg).
      '''
      ev = event.EventHandlerInfo(widget, func)
      self._widgetEvent -= ev

    def addMenuEvent(self, menuItem, func, sendMenuItem=False):
      '''
      Add new Menu item event handler function.
      Event handler function must be defined like func(owner, earg).
      If sendMenuItem is True func must be defined as func(owner, item, earg)
      and involved menu item is passed to handler
      '''
      ev = event.EventHandlerInfo(menuItem, func, sendMenuItem)
      self._menuEvent += ev
    
    def removeMenuEvent(self, menuItem, func=None):
      '''
      Add new Menu item event handler function.
      Event handler function must be defined like func(owner, earg).
      '''
      ev = event.EventHandlerInfo(menuItem, func)
      self._menuEvent -= ev

    def widgetEvent(self, widget, *args, **kargs):
      ''' 
      send a widget event
      '''
      self._widgetEvent(widget, *args, **kargs)
 
    def timeoutEvent(self, *args, **kargs):
      ''' 
      send a timeout event
      '''
      self._timeoutEvent("__timeout__", *args, **kargs)

    def cancelEvent(self, *args, **kargs):
      ''' 
      send a cancel event
      '''
      self._cancelEvent("__cancel__", *args, **kargs)
      
    def menuEvent(self, menuItem, *args, **kargs):
      ''' 
      send a Menu item event
      '''
      self._menuEvent(menuItem, *args, **kargs)
 
