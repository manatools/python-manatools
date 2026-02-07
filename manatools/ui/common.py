# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.ui.common contains all the UI classes and tools that 
could be useful int a manatools application

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.ui.common
'''

from ..aui import yui
from enum import Enum
import gettext
# https://pymotw.com/3/gettext/#module-localization
t = gettext.translation(
    'python-manatools',
    '/usr/share/locale',
    fallback=True,
)
_ = t.gettext
ngettext = t.ngettext

def destroyUI () :
    '''
    Best-effort teardown for AUI dialogs. AUI manages backend lifecycle internally,
    so there is typically no need to manually destroy UI plugins as in libyui.
    This function exists for API compatibility and currently performs no action.
    '''
    return


def warningMsgBox (info) :
    '''
    This function creates a Warning dialog and shows the message passed as input.

    @param info: dictionary, information to be passed to the dialog.
            title     =>     dialog title
            text      =>     string to be shown into the dialog
            richtext  =>     True if using rich text
    '''
    if not info:
        return 0

    factory = yui.YUI.widgetFactory()
    dlg = factory.createPopupDialog()
    vbox = factory.createVBox(dlg)

    # Heading
    title = info.get('title')
    if title:
        factory.createHeading(vbox, title)

    # Content row: icon + text
    text = info.get('text', "") or ""
    rt = bool(info.get('richtext', False))
    row = factory.createHBox(vbox)

    # Icon (warning)
    try:
        icon_align = factory.createTop(row)
        icon = factory.createImage(icon_align, "dialog-warning")
        icon.setStretchable(yui.YUIDimension.YD_VERT, False)
        icon.setStretchable(yui.YUIDimension.YD_HORIZ, False)
        icon.setAutoScale(False)
    except Exception:
        # If icon creation fails, continue without it
        pass

    # Text widget
    if rt:
        tw = factory.createRichText(row, "", False)
        tw.setValue(text)
    else:
        tw = factory.createLabel(row, text)
    try:
        tw.setStretchable(yui.YUIDimension.YD_HORIZ, True)
        tw.setStretchable(yui.YUIDimension.YD_VERT, True)
    except Exception:
        pass

    # Ok button on the right
    btns = factory.createHBox(vbox)
    factory.createHStretch(btns)
    ok_btn = factory.createPushButton(btns, _("&Ok"))

    # Event loop
    while True:
        ev = dlg.waitForEvent()
        et = ev.eventType()
        if et in (yui.YEventType.CancelEvent, yui.YEventType.TimeoutEvent):
            break
        if et == yui.YEventType.WidgetEvent and ev.widget() == ok_btn and ev.reason() == yui.YEventReason.Activated:
            break

    dlg.destroy()
    return 1


def infoMsgBox (info) :
    '''
    This function creates an Info dialog and shows the message passed as input.

    @param info: dictionary, information to be passed to the dialog.
            title     =>     dialog title
            text      =>     string to be shown into the dialog
            richtext  =>     True if using rich text
    '''
    if not info:
        return 0

    factory = yui.YUI.widgetFactory()
    dlg = factory.createPopupDialog()
    vbox = factory.createVBox(dlg)

    # Heading
    title = info.get('title')
    if title:
        factory.createHeading(vbox, title)

    # Content row: icon + text
    text = info.get('text', "") or ""
    rt = bool(info.get('richtext', False))    
    row = factory.createHBox(vbox)

    # Icon (information)
    try:
        icon_align = factory.createTop(row)
        icon = factory.createImage(icon_align, "dialog-information")
        icon.setStretchable(yui.YUIDimension.YD_VERT, False)
        icon.setStretchable(yui.YUIDimension.YD_HORIZ, False)
        icon.setAutoScale(False)
    except Exception:
        pass

    # Text widget
    if rt:
        tw = factory.createRichText(row, "", False)
        tw.setValue(text)
    else:
        tw = factory.createLabel(row, text)
    try:
        tw.setStretchable(yui.YUIDimension.YD_HORIZ, True)
        tw.setStretchable(yui.YUIDimension.YD_VERT, True)
    except Exception:
        pass

    # Ok button on the right
    btns = factory.createHBox(vbox)
    factory.createHStretch(btns)
    ok_btn = factory.createPushButton(btns, _("&Ok"))

    # Event loop
    while True:
        ev = dlg.waitForEvent()
        et = ev.eventType()
        if et in (yui.YEventType.CancelEvent, yui.YEventType.TimeoutEvent):
            break
        if et == yui.YEventType.WidgetEvent and ev.widget() == ok_btn and ev.reason() == yui.YEventReason.Activated:
            break

    dlg.destroy()
    return 1


def msgBox (info) :
    '''
    This function creates a dialog and shows the message passed as input.

    @param info: dictionary, information to be passed to the dialog.
            title     =>     dialog title
            text      =>     string to be shown into the dialog
            richtext  =>     True if using rich text
    '''
    if not info:
        return 0

    factory = yui.YUI.widgetFactory()
    dlg = factory.createPopupDialog()
    vbox = factory.createVBox(dlg)

    # Heading
    title = info.get('title')
    if title:
        factory.createHeading(vbox, title)

    # Content row: text only (no icon)
    text = info.get('text', "") or ""
    rt = bool(info.get('richtext', False))    
    row = factory.createHBox(vbox)

    # Text widget
    if rt:
        tw = factory.createRichText(row, "", False)
        tw.setValue(text)
    else:
        tw = factory.createLabel(row, text)
    try:
        tw.setStretchable(yui.YUIDimension.YD_HORIZ, True)
        tw.setStretchable(yui.YUIDimension.YD_VERT, True)
    except Exception:
        pass

    # Ok button on the right
    btns = factory.createHBox(vbox)
    factory.createHStretch(btns)
    ok_btn = factory.createPushButton(btns, _("&Ok"))

    # Event loop
    while True:
        ev = dlg.waitForEvent()
        et = ev.eventType()
        if et in (yui.YEventType.CancelEvent, yui.YEventType.TimeoutEvent):
            break
        if et == yui.YEventType.WidgetEvent and ev.widget() == ok_btn and ev.reason() == yui.YEventReason.Activated:
            break

    dlg.destroy()
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

    factory = yui.YUI.widgetFactory()
    dlg = factory.createPopupDialog()
    vbox = factory.createVBox(dlg)

    # Heading
    title = info.get('title')
    if title:
        factory.createHeading(vbox, title)

    # Content row: icon + text
    text = info.get('text', "") or ""
    rt = bool(info.get('richtext', False))
    row = factory.createHBox(vbox)

    # Icon (information)
    try:
        icon_align = factory.createTop(row)
        icon = factory.createImage(icon_align, "dialog-information")
        icon.setStretchable(yui.YUIDimension.YD_VERT, False)
        icon.setStretchable(yui.YUIDimension.YD_HORIZ, False)
        icon.setAutoScale(False)
    except Exception:
        pass

    # Text widget
    if rt:
        tw = factory.createRichText(row, "", False)
        tw.setValue(text)
    else:
        tw = factory.createLabel(row, text)
    try:
        tw.setStretchable(yui.YUIDimension.YD_HORIZ, True)
        tw.setStretchable(yui.YUIDimension.YD_VERT, True)
    except Exception:
        pass

    # Buttons on the right
    btns = factory.createHBox(vbox)
    factory.createHStretch(btns)
    ok_btn = factory.createPushButton(btns, _("&Ok"))
    cancel_btn = factory.createPushButton(btns, _("&Cancel"))

    default_ok = bool(info.get('default_button', 0) == 1)
    # simple default: ignore focusing specifics for now
    result = False
    while True:
        ev = dlg.waitForEvent()
        et = ev.eventType()
        if et == yui.YEventType.CancelEvent:
            result = False
            break
        if et == yui.YEventType.WidgetEvent:
            w = ev.widget()
            if w == ok_btn and ev.reason() == yui.YEventReason.Activated:
                result = True
                break
            if w == cancel_btn and ev.reason() == yui.YEventReason.Activated:
                result = False
                break
    dlg.destroy()
    return result

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

    factory = yui.YUI.widgetFactory()
    dlg = factory.createPopupDialog()
    vbox = factory.createVBox(dlg)

    # Heading
    title = info.get('title')
    if title:
        factory.createHeading(vbox, title)

    # Content row: icon + text
    text = info.get('text', "") or ""
    rt = bool(info.get('richtext', False))    
    row = factory.createHBox(vbox)

    # Icon (question)
    try:
        icon_align = factory.createTop(row)
        icon = factory.createImage(icon_align, "dialog-question")
        icon.setStretchable(yui.YUIDimension.YD_VERT, False)
        icon.setStretchable(yui.YUIDimension.YD_HORIZ, False)
        icon.setAutoScale(False)
    except Exception:
        pass

    # Text widget
    if rt:
        tw = factory.createRichText(row, "", False)
        tw.setValue(text)
    else:
        tw = factory.createLabel(row, text)
    try:
        tw.setStretchable(yui.YUIDimension.YD_HORIZ, True)
        tw.setStretchable(yui.YUIDimension.YD_VERT, True)
    except Exception:
        pass

    # Handle size if provided
    if 'size' in info.keys():
        try:
            dims = info['size']
            parent = factory.createMinSize(vbox, int(dims[0]), int(dims[1]))
            vbox = parent
        except Exception:
            pass

    # Buttons on the right
    btns = factory.createHBox(vbox)
    factory.createHStretch(btns)
    yes_btn = factory.createPushButton(btns, _("&Yes"))
    no_btn = factory.createPushButton(btns, _("&No"))

    result = False
    while True:
        ev = dlg.waitForEvent()
        et = ev.eventType()
        if et == yui.YEventType.CancelEvent:
            result = False
            break
        if et == yui.YEventType.WidgetEvent:
            w = ev.widget()
            if w == yes_btn and ev.reason() == yui.YEventReason.Activated:
                result = True
                break
            if w == no_btn and ev.reason() == yui.YEventReason.Activated:
                result = False
                break
    dlg.destroy()
    return result

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

    # Build a simple About dialog using AUI widgets
    factory = yui.YUI.widgetFactory()
    dlg = factory.createPopupDialog()
    vbox = factory.createVBox(dlg)

    name        = info.get('name', "")
    version     = info.get('version', "")
    license_txt = info.get('license', "")
    authors     = info.get('authors', "")
    description = info.get('description', "")
    logo        = info.get('logo', "")
    credits     = info.get('credits', "")
    information = info.get('information', "")

    title = _("About") + (f" {name}" if name else "")
    factory.createHeading(vbox, title)

    # Header block
    header = factory.createHBox(vbox)
    if logo:
        try:
            factory.createImage(header, logo)
            factory.createHSpacing(header, 8)
        except Exception:
            pass
    labels = factory.createVBox(header)
    if name:
        factory.createLabel(labels, name)
    if version:
        factory.createLabel(labels, version)
    if license_txt:
        factory.createLabel(labels, license_txt)

    # Content block
    if description:
        rt = factory.createRichText(vbox, "", False)
        rt.setValue(description)
    if authors:
        factory.createHeading(vbox, _("Authors"))
        ra = factory.createRichText(vbox, "", False)
        ra.setValue(authors)
    if credits:
        factory.createHeading(vbox, _("Credits"))
        rc = factory.createRichText(vbox, "", False)
        rc.setValue(credits)
    if information:
        factory.createHeading(vbox, _("Information"))
        ri = factory.createRichText(vbox, "", False)
        ri.setValue(information)

    align = factory.createRight(vbox)
    close_btn = factory.createPushButton(align, _("&Close"))
    while True:
        ev = dlg.waitForEvent()
        if ev.eventType() in (yui.YEventType.CancelEvent, yui.YEventType.TimeoutEvent):
            break
        if ev.eventType() == yui.YEventType.WidgetEvent and ev.widget() == close_btn and ev.reason() == yui.YEventReason.Activated:
            break
    dlg.destroy()
