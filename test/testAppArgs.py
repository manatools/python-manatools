# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:

'''
Test services 

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools
'''

import manatools.args as args


if __name__ == '__main__':
  parser = args.AppArgs('command')
  if parser.args.version:
      print("v1")
      
      
