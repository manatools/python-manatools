'''
Python manatools.args contains an base for parsing argument passed from command line.

License: LGPLv2+

Author:  Papoteur 

@package mamatools.args
'''
import argparse
import gettext

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
        # libyui pass through arguments
        ui_select_parser.add_argument('--gtk', help=_('start using yui GTK+ plugin implementation'), action='store_true')
        ui_select_parser.add_argument('--ncurses', help=_('start using yui ncurses plugin implementation'), action='store_true')
        ui_select_parser.add_argument('--qt', help=_('start using yui Qt plugin implementation'), action='store_true')
        self.parser.add_argument('--fullscreen', help=_('use full screen for dialogs'), action='store_true')

        # Application arguments
        self.parser.add_argument('--locales-dir', nargs='?', help=_('directory containing localization strings (developer only)'))
        self.parser.add_argument('--version',     help=_('show application version and exit'), action='store_true')

    @property
    def args(self) :
        '''
        returns args parsed from command line
        '''
        return self.parser.parse_args()



        # Change localedir if "--locales-dir" option is specified
        if args.locales_dir:
            gettext.install(command, localedir=args.locales_dir, names=('ngettext',))
