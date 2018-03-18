# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Event class

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools
'''

class EventHandlerInfo:
  def __init__(self, obj, handler, sendObj=False):
    self.object = obj
    self.handler = handler
    self.sendObjectOnEventCallBack = sendObj

  def __eq__(self, other):
    """Override the default Equals behavior"""
    if isinstance(other, self.__class__):
        #return self.__dict__ == other.__dict__
        return self.object == other.object and self.handler == other.handler
    raise TypeError("Wrong type")

  def __ne__(self, other):
    """Define a non-equality test"""
    if isinstance(other, self.__class__):
        return not self.__eq__(other)
    raise TypeError("Wrong type")

  def __hash__(self):
    """Override the default hash behavior (that returns the id or the object)"""
    return id(tuple(sorted(self.__dict__.items())))

  
class Event:
    def __init__(self):
      self.handlers = set()

    def handle(self, handler):
      if isinstance(handler, EventHandlerInfo):
        self.handlers.add(handler)
      else :
        raise TypeError("Wrong handler type")
      return self

    def unhandle(self, handler):
      if not isinstance(handler, EventHandlerInfo):
        raise TypeError("Wrong handler type")
      try:
        self.handlers.remove(handler)
      except:
        raise ValueError("Handler is not handling this event, so cannot unhandle it.")
      return self

    def fire(self, obj, *args, **kargs):
      for handler in self.handlers:
        if handler.object == obj :
          if handler.sendObjectOnEventCallBack :
            handler.handler(handler.object, *args, **kargs)
          else:
            handler.handler(*args, **kargs)

    def getHandlerCount(self):
        return len(self.handlers)

    __iadd__ = handle
    __isub__ = unhandle
    __call__ = fire
    __len__  = getHandlerCount


