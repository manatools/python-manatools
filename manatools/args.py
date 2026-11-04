'''
Python manatools.args contains an base for parsing argument passed from command line.

License: LGPLv2+

Author:  Papoteur 

@package manatools.args
'''
import argparse
import gettext
import os
import sys

class AppArgs :
    '''
    AppArs contains an base for parsing argument passed from command line.
    command is the application name
    It can be superseded to add specific options
    '''
    def __init__(self, command, localedir='/usr/share/locale', strings_domain='python-manatools') :

        # Windows has no /usr/share/locale; None selects gettext's default,
        # <sys.base_prefix>/share/locale
        if sys.platform == 'win32' and localedir == '/usr/share/locale':
            localedir = None
        translator = gettext.translation(strings_domain, localedir=localedir, fallback=True)
        tr = translator.gettext

        usage = '%%(prog)s [%s]' % tr('options')
        self.parser = argparse.ArgumentParser(prog=command, usage=usage)
        if getattr(self.parser, '_optionals', None) is not None:
            self.parser._optionals.title = tr('options')
        for action in self.parser._actions:
            if '--help' in action.option_strings:
                action.help = tr('show this help message and exit')
        ui_select_parser = self.parser.add_mutually_exclusive_group()
        # force manatools aui backend
        ui_select_parser.add_argument('--gtk', help=tr('start using Gtk backend'), action='store_true')
        ui_select_parser.add_argument('--ncurses', help=tr('start using ncurses backend'), action='store_true')
        ui_select_parser.add_argument('--qt', help=tr('start using Qt backend'), action='store_true')

        # Application arguments
        self.parser.add_argument('--locales-dir', nargs='?', help=tr('directory containing localization strings (developer only)'))
        self.parser.add_argument('--version',     help=tr('show application version and exit'), action='store_true')

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
