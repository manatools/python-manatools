# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.ui.common contains all the UI classes and tools that 
could be useful int a manatools application

License: GPLv3

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.ui.common
'''

import yui
import gettext


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

