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
from ..aui.yui_common import YUIDimension
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


def _push_app_title(new_title):
    """Save current application title and optionally set a new one."""
    try:
        app = yui.YUI.app()
        old_title = app.applicationTitle()
        if new_title:
            app.setApplicationTitle(str(new_title))
        return old_title
    except Exception:
        return None


def _restore_app_title(old_title):
    """Restore the previously saved application title."""    
    app = yui.YUI.app()
    try:
        if old_title is not None:
            app.setApplicationTitle(str(old_title))
    except Exception:
        pass

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

    dlg = None
    try:
        factory = yui.YUI.widgetFactory()
        dlg = factory.createPopupDialog()
        title = info.get('title')
        old_title = _push_app_title(title)

        vbox = factory.createVBox(dlg)

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
        factory.createHStretch(btns)

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
    finally:
        if dlg is not None:
            try:
                dlg.destroy()
            except Exception:
                pass
        _restore_app_title(old_title)

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

    dlg = None
    try:
        factory = yui.YUI.widgetFactory()
        dlg = factory.createPopupDialog()
        title = info.get('title')
        old_title = _push_app_title(title)

        vbox = factory.createVBox(dlg)

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
        factory.createHStretch(btns)

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
    finally:
        if dlg is not None:
            try:
                dlg.destroy()
            except Exception:
                pass
        _restore_app_title(old_title)

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

    dlg = None
    try:
        factory = yui.YUI.widgetFactory()
        dlg = factory.createPopupDialog()
        title = info.get('title')
        old_title = _push_app_title(title)
        vbox = factory.createVBox(dlg)

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
        factory.createHStretch(btns)

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
    finally:
        if dlg is not None:
            try:
                dlg.destroy()
            except Exception:
                pass
        _restore_app_title(old_title)

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

    dlg = None
    try:
        factory = yui.YUI.widgetFactory()
        dlg = factory.createPopupDialog()
        title = info.get('title')
        old_title = _push_app_title(title)

        vbox = factory.createVBox(dlg)

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
    finally:
        if dlg is not None:
            try:
                dlg.destroy()
            except Exception:
                pass
        _restore_app_title(old_title)

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

    dlg = None
    try:
        factory = yui.YUI.widgetFactory()
        dlg = factory.createPopupDialog()
        title = info.get('title')
        old_title = _push_app_title(title)
        vbox = factory.createVBox(dlg)

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
    finally:
        if dlg is not None:
            try:
                dlg.destroy()
            except Exception:
                pass
        _restore_app_title(old_title)

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
    
    dlg = None
    try:
        factory = yui.YUI.widgetFactory()
        dlg = factory.createPopupDialog()
        title = _("About") + " " + info.get('name', "")
        old_title = _push_app_title(title)
        root_vbox = factory.createVBox(dlg)

        # Optional MinSize wrapper (accepts {'column','lines'} like the C++ code)
        content_parent = root_vbox
        size_hint = info.get('size') or {}
        try:
            cols = int(size_hint.get('column', size_hint.get('columns')))
            rows = int(size_hint.get('lines', size_hint.get('rows')))
            content_parent = factory.createMinSize(root_vbox, cols, rows)
        except Exception:
            content_parent = root_vbox

        vbox = factory.createVBox(content_parent)

        name        = info.get('name', "")
        version     = info.get('version', "")
        license_txt = info.get('license', "")
        authors     = info.get('authors', "")
        description = info.get('description', "")
        logo        = info.get('logo', "")
        credits     = info.get('credits', "")
        information = info.get('information', "")
        dialog_mode = info.get('dialog_mode', AboutDialogMode.CLASSIC)

        # Header block (logo + labels)
        header = factory.createHBox(vbox)
        if logo:
            try:
                factory.createImage(header, logo)
                factory.createSpacing(header, 8)
            except Exception:
                pass
        labels = factory.createVBox(header)
        if name:
            factory.createLabel(labels, name)
        if version:
            factory.createLabel(labels, version)
        if license_txt:
            factory.createLabel(labels, license_txt)

        # Credits line (matches C++ layout)
        if credits:
            credits_box = factory.createHBox(vbox)
            factory.createSpacing(credits_box, 1)
            factory.createLabel(credits_box, credits)
            factory.createSpacing(credits_box, 1)
            # ...existing code...

        # Helper to add a RichText block
        def _add_richtext(parent, value):
            rt = factory.createRichText(parent, "", False)
            rt.setValue(value)
            try:
                rt.setStretchable(YUIDimension.YD_HORIZ, True)
                rt.setStretchable(YUIDimension.YD_VERT, True)
            except Exception:
                pass
            return rt

        info_btn = None
        credits_btn = None

        # Tabbed layout (Authors / Description / Information) if requested and available
        use_tabbed = (dialog_mode == AboutDialogMode.TABBED)
        tab_widget = None
        if use_tabbed:
            try:
                tab_widget = factory.createDumbTab(vbox)
            except Exception:
                tab_widget = None
            if tab_widget:
                sections_added = False
                if authors:
                    tab_authors = tab_widget.addItem(_("Authors"))
                    _add_richtext(tab_authors, authors)
                    sections_added = True
                if description:
                    tab_desc = tab_widget.addItem(_("Description"))
                    _add_richtext(tab_desc, description)
                    sections_added = True
                if information:
                    tab_info = tab_widget.addItem(_("Information"))
                    _add_richtext(tab_info, information)
                    sections_added = True
                if not sections_added:
                    tab_widget = None
            if tab_widget is None:
                use_tabbed = False  # fallback to classic if tabs unavailable

        if not use_tabbed:
            # Classic stacked content + buttons (mirrors C++ behavior)
            if description:
                factory.createHeading(vbox, _("Description"))
                _add_richtext(vbox, description)
            if authors:
                factory.createHeading(vbox, _("Authors"))
                _add_richtext(vbox, authors)
            if information:
                factory.createHeading(vbox, _("Information"))
                _add_richtext(vbox, information)
            button_row = factory.createHBox(vbox)
            if information:
                info_btn = factory.createPushButton(button_row, _("&Info"))
            if credits:
                credits_btn = factory.createPushButton(button_row, _("&Credits"))

        # Close button aligned to the right, as in the C++ dialog
        close_row = factory.createHBox(vbox)
        factory.createHStretch(close_row)
        close_btn = factory.createPushButton(close_row, _("&Close"))

        while True:
            ev = dlg.waitForEvent()
            if not ev:
                continue
            et = ev.eventType()
            if et in (yui.YEventType.CancelEvent, yui.YEventType.TimeoutEvent):
                break
            if et != yui.YEventType.WidgetEvent:
                continue
            widget = ev.widget()
            if widget == close_btn:
                break
            if info_btn and widget == info_btn:
                infoMsgBox({"title": _("Information"), "text": information or "", "richtext": True})
            elif credits_btn and widget == credits_btn:
                infoMsgBox({"title": _("Credits"), "text": credits or "", "richtext": True})

        dlg.destroy()
    finally:
        if dlg is not None:
            try:
                dlg.destroy()
            except Exception:
                pass
        _restore_app_title(old_title)
