# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:

'''
Test services 

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools
'''

import manatools.services as services


if __name__ == '__main__':
  serv = services.Services()
  units = serv.service_info
  
  for u in units.keys():
      print ("%s: %s <<%s>>"%(u, units[u]['name'], units[u]['description']))
