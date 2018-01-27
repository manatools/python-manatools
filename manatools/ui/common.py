# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.ui.common contains all the UI classes and tools that 
could be useful int a manatools application

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.ui.common
'''

import yui
import gettext
from enum import Enum


def destroyUI () :
    '''
    destroy all the dialogs and delete YUI plugins. Use this at the very end of your application
    to close everything correctly, expecially if you experience a crash in Qt plugin as explained 
    into ussue https://github.com/libyui/libyui-qt/issues/41
    '''
    yui.YDialog.deleteAllDialogs()
    # next line seems to be a workaround to prevent the qt-app from crashing
    # see https://github.com/libyui/libyui-qt/issues/41
    yui.YUILoader.deleteUI()


def warningMsgBox (info) :
    '''
    This function creates an Warning dialog and show the message
    passed as input.

    @param info: dictionary, information to be passed to the dialog.
            title     =>     dialog title
            text      =>     string to be swhon into the dialog
            richtext  =>     True if using rich text
    '''
    if (not info) :
        return 0

    gettext.install('python-manatools', localedir='/usr/share/locale')

    retVal = 0
    yui.YUI.widgetFactory
    factory = yui.YExternalWidgets.externalWidgetFactory("mga")
    factory = yui.YMGAWidgetFactory.getYMGAWidgetFactory(factory)
    dlg = factory.createDialogBox(yui.YMGAMessageBox.B_ONE, yui.YMGAMessageBox.D_WARNING)

    if ('title' in info.keys()) :
        dlg.setTitle(info['title'])

    rt = False
    if ("richtext" in info.keys()) :
        rt = info['richtext']

    if ('text' in info.keys()) :
        dlg.setText(info['text'], rt)

    dlg.setButtonLabel(_("&Ok"), yui.YMGAMessageBox.B_ONE )
#   dlg.setMinSize(50, 5)

    retVal = dlg.show()
    dlg = None

    return 1


def infoMsgBox (info) :
    '''
    This function creates an Info dialog and show the message
    passed as input.

    @param info: dictionary, information to be passed to the dialog.
            title     =>     dialog title
            text      =>     string to be swhon into the dialog
            richtext  =>     True if using rich text
    '''
    if (not info) :
        return 0

    retVal = 0
    yui.YUI.widgetFactory
    factory = yui.YExternalWidgets.externalWidgetFactory("mga")
    factory = yui.YMGAWidgetFactory.getYMGAWidgetFactory(factory)
    dlg = factory.createDialogBox(yui.YMGAMessageBox.B_ONE, yui.YMGAMessageBox.D_INFO)

    if ('title' in info.keys()) :
        dlg.setTitle(info['title'])

    rt = False
    if ("richtext" in info.keys()) :
        rt = info['richtext']

    if ('text' in info.keys()) :
        dlg.setText(info['text'], rt)

    dlg.setButtonLabel(_("&Ok"), yui.YMGAMessageBox.B_ONE )
#   dlg.setMinSize(50, 5)

    retVal = dlg.show()
    dlg = None

    return 1

def msgBox (info) :
    '''
    This function creates a dialog and show the message passed as input.

    @param info: dictionary, information to be passed to the dialog.
            title     =>     dialog title
            text      =>     string to be swhon into the dialog
            richtext  =>     True if using rich text
    '''
    if (not info) :
        return 0

    retVal = 0
    yui.YUI.widgetFactory
    factory = yui.YExternalWidgets.externalWidgetFactory("mga")
    factory = yui.YMGAWidgetFactory.getYMGAWidgetFactory(factory)
    dlg = factory.createDialogBox(yui.YMGAMessageBox.B_ONE)

    if ('title' in info.keys()) :
        dlg.setTitle(info['title'])

    rt = False
    if ("richtext" in info.keys()) :
        rt = info['richtext']

    if ('text' in info.keys()) :
        dlg.setText(info['text'], rt)

    dlg.setButtonLabel(_("&Ok"), yui.YMGAMessageBox.B_ONE )
#   dlg.setMinSize(50, 5)

    retVal = dlg.show()
    dlg = None

    return 1


def askOkCancel (info) :
    '''
    This function create an OK-Cancel dialog with a <<title>> and a
    <<text>> passed as parameters.

    @param info: dictionary, information to be passed to the dialog.
        title     =>     dialog title
        text      =>     string to be swhon into the dialog
        richtext  =>     True if using rich text
        default_button => optional default button [1 => Ok - any other values => Cancel]

    @output:
        False: Cancel button has been pressed
        True:  Ok button has been pressed
    '''
    if (not info) :
        return False

    retVal = False
    yui.YUI.widgetFactory
    factory = yui.YExternalWidgets.externalWidgetFactory("mga")
    factory = yui.YMGAWidgetFactory.getYMGAWidgetFactory(factory)
    dlg = factory.createDialogBox(yui.YMGAMessageBox.B_TWO)

    if ('title' in info.keys()) :
        dlg.setTitle(info['title'])

    rt = False
    if ("richtext" in info.keys()) :
        rt = info['richtext']

    if ('text' in info.keys()) :
        dlg.setText(info['text'], rt)

    dlg.setButtonLabel(_("&Ok"), yui.YMGAMessageBox.B_ONE )
    dlg.setButtonLabel(_("&Cancel"), yui.YMGAMessageBox.B_TWO )

    if ("default_button" in info.keys() and info["default_button"] == 1) :
        dlg.setDefaultButton(yui.YMGAMessageBox.B_ONE)
    else :
        dlg.setDefaultButton(yui.YMGAMessageBox.B_TWO)

    dlg.setMinSize(50, 5)

    retVal = dlg.show() == yui.YMGAMessageBox.B_ONE;
    dlg = None

    return retVal

def askYesOrNo (info) :
    '''
    This function create an Yes-No dialog with a <<title>> and a
    <<text>> passed as parameters.

    @param info: dictionary, information to be passed to the dialog.
        title     =>     dialog title
        text      =>     string to be swhon into the dialog
        richtext  =>     True if using rich text
        default_button => optional default button [1 => Yes - any other values => No]
        size => [row, coulmn]

    @output:
        False: No button has been pressed
        True:  Yes button has been pressed
    '''
    if (not info) :
        return False

    retVal = False
    yui.YUI.widgetFactory
    factory = yui.YExternalWidgets.externalWidgetFactory("mga")
    factory = yui.YMGAWidgetFactory.getYMGAWidgetFactory(factory)
    dlg = factory.createDialogBox(yui.YMGAMessageBox.B_TWO)

    if ('title' in info.keys()) :
        dlg.setTitle(info['title'])

    rt = False
    if ("richtext" in info.keys()) :
        rt = info['richtext']

    if ('text' in info.keys()) :
        dlg.setText(info['text'], rt)

    dlg.setButtonLabel(_("&Yes"), yui.YMGAMessageBox.B_ONE )
    dlg.setButtonLabel(_("&No"), yui.YMGAMessageBox.B_TWO )
    if ("default_button" in info.keys() and info["default_button"] == 1) :
        dlg.setDefaultButton(yui.YMGAMessageBox.B_ONE)
    else :
        dlg.setDefaultButton(yui.YMGAMessageBox.B_TWO)
    if ('size' in info.keys()) :
        dlg.setMinSize(info['size'][0], info['size'][1])

    retVal = dlg.show() == yui.YMGAMessageBox.B_ONE;
    dlg = None

    return retVal

class AboutDialogMode(Enum):
    '''
    Enum
        CLASSIC for classic about dialog
        TABBED  for tabbed about dialog
    '''
    CLASSIC = 1
    TABBED  = 2

def AboutDialog (info) :
    '''
    About dialog implementation. AboutDialog can be used by
    modules, to show authors, license, credits, etc.

    @param info: dictionary, optional information to be passed to the dialog.
        name        => the application name
        version     =>  the application version
        license     =>  the application license, the short length one (e.g. GPLv2, GPLv3, LGPLv2+, etc)
        authors     =>  the string providing the list of authors; it could be html-formatted
        description =>  the string providing a brief description of the application
        logo        => the string providing the file path for the application logo (high-res image)
        icon        => the string providing the file path for the application icon (low-res image)
        credits     => the application credits, they can be html-formatted
        information => other extra informations, they can be html-formatted
        size        => libyui dialog minimum size, dictionary containing {column, lines}
        dialog_mode => AboutDialogMode.CLASSIC: classic style dialog, any other as tabbed style dialog
    '''
    if (not info) :
        raise ValueError("Missing AboutDialog parameters")

    yui.YUI.widgetFactory
    factory = yui.YExternalWidgets.externalWidgetFactory("mga")
    factory = yui.YMGAWidgetFactory.getYMGAWidgetFactory(factory)

    name        = info['name'] if 'name' in info.keys() else ""
    version     = info['version'] if 'version' in info.keys() else ""
    license     = info['license'] if 'license' in info.keys() else ""
    authors     = info['authors'] if 'authors' in info.keys() else ""
    description = info['description'] if 'description' in info.keys() else ""
    logo        = info['logo'] if 'logo' in info.keys() else ""
    icon        = info['icon'] if 'icon' in info.keys() else ""
    credits     = info['credits'] if 'credits' in info.keys() else ""
    information = info['information'] if 'information' in info.keys() else ""
    dialog_mode = yui.YMGAAboutDialog.TABBED
    if 'dialog_mode' in info.keys() :
        dialog_mode = yui.YMGAAboutDialog.CLASSIC if info['dialog_mode'] == AboutDialogMode.CLASSIC else yui.YMGAAboutDialog.TABBED

    dlg = factory.createAboutDialog(name, version, license,
                                    authors, description, logo,
                                    icon, credits, information
    )
    if 'size' in info.keys():
        if not 'column' in info['size'] or  not 'lines' in info['size'] :
            raise ValueError("size must contains <<column>> and <<lines>> keys")
        dlg.setMinSize(info['size']['column'], info['size']['lines'])

    dlg.show(dialog_mode)
    dlg = None
