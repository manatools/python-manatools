# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.basehelpinfo contains all the Help information base class
that should be use for help dialog

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.basehelpinfo
'''

class HelpInfoBase:
  def __init__(self):
    pass

  def show(self, info_to_show):
    '''
    super class must implement show to return the right string to show
    into dialog
    @param info_to_show: a kind of index of what to show, it depends on implementation
    '''
    raise NotImplementedError("show is not implemented")

  def home(self):
    '''
    super class must implement show to return the very first info to show
    into dialog, such as index for instance. Than index could be anchored and anchors passed
    to show() to display related content
    '''
    raise NotImplementedError("home is not implemented")
