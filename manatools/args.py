'''
Python manatools.args contains an base for parsing argument passed from command line.

License: LGPLv2+

Author:  Papoteur 

@package manatools.args
'''
import argparse
import gettext
import os

class AppArgs :
    '''
    AppArs contains an base for parsing argument passed from command line.
    command is the application name
    It can be superseded to add specific options
    '''
    def __init__(self, command) :

        # We need to call this as early as possible because
        # command-line help strings are translated
        gettext.install(command, localedir='/usr/share/locale', names=('ngettext',))
        self.parser = argparse.ArgumentParser(prog=command, usage='%(prog)s [options]')
        ui_select_parser = self.parser.add_mutually_exclusive_group()
        # force manatools aui backend
        ui_select_parser.add_argument('--gtk', help=_('start using Gtk backend'), action='store_true')
        ui_select_parser.add_argument('--ncurses', help=_('start using ncurses backend'), action='store_true')
        ui_select_parser.add_argument('--qt', help=_('start using Qt backend'), action='store_true')

        # Application arguments
        self.parser.add_argument('--locales-dir', nargs='?', help=_('directory containing localization strings (developer only)'))
        self.parser.add_argument('--version',     help=_('show application version and exit'), action='store_true')

        self._args = None

    @property
    def args(self) :
        '''
        Returns args parsed from command line.
        If --gtk, --ncurses, or --qt is given, sets MUI_BACKEND accordingly so
        that manatools.aui.yui uses that backend directly, bypassing auto-detection.
        '''
        if self._args is None:
            self._args = self.parser.parse_args()
            if self._args.gtk:
                os.environ['MUI_BACKEND'] = 'gtk'
            elif self._args.ncurses:
                os.environ['MUI_BACKEND'] = 'ncurses'
            elif self._args.qt:
                os.environ['MUI_BACKEND'] = 'qt'
        return self._args
