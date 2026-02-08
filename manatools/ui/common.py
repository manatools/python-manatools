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
from ..aui.yui_common import YUIDimension, YItem
from enum import Enum
import gettext
import logging
import warnings
# https://pymotw.com/3/gettext/#module-localization
t = gettext.translation(
    'python-manatools',
    '/usr/share/locale',
    fallback=True,
)
_ = t.gettext
ngettext = t.ngettext

logger = logging.getLogger("manatools.ui.common")

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
        size => [width, height] in pixels, optional dialog minimum size hint

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
                parent = factory.createMinSize(vbox, int(dims.get('width', 320)), int(dims.get('height', 240)))
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

def AboutDialog(info=None, *, dialog_mode: AboutDialogMode = AboutDialogMode.CLASSIC, size=None):
    '''
    About dialog implementation. AboutDialog can be used by
    modules to show authors, license, credits, etc.

    Parameters
    ----------
    info: dict | None
        Deprecated dictionary that historically provided dialog metadata.
        Present values still override backend metadata, but callers should
        prefer configuring fields via the application backend. When provided
        a DeprecationWarning is emitted.
    dialog_mode: AboutDialogMode
        Target layout style (classic/tabbed). Defaults to CLASSIC.
    size: Mapping | Sequence | None
        Optional minimum-size hint. Accepted formats:
            - mapping containing 'width'/'height' (or legacy 'column'/'lines')
            - tuple/list where the first element is width and the second height
    '''

    safe_info = {}
    if info is not None:
        if not isinstance(info, dict):
            raise TypeError("info must be a dict when provided")
        safe_info = dict(info)
        warnings.warn(
            "AboutDialog 'info' parameter is deprecated; configure metadata via the application backend.",
            DeprecationWarning,
            stacklevel=2,
        )
        logger.warning("AboutDialog 'info' parameter is deprecated; prefer backend metadata.")

    app = None
    try:
        app = yui.YUI.app()
    except Exception as exc:
        logger.debug("Unable to obtain YUI application instance: %s", exc)

    def _fetch_value(info_key, app_attr, fallback=""):
        if safe_info.get(info_key):
            return safe_info.get(info_key)
        if app is None:
            return fallback
        value = None
        attr = getattr(app, app_attr, None)
        try:
            value = attr() if callable(attr) else attr
        except Exception as exc:
            logger.debug("Unable to fetch %s via %s: %s", info_key, app_attr, exc)
            value = None
        if (not value) and info_key == 'name':
            try:
                value = app.productName()
            except Exception:
                pass
        return value or fallback

    name        = _fetch_value('name', 'applicationName')
    version     = _fetch_value('version', 'version')
    license_txt = _fetch_value('license', 'license')
    authors     = _fetch_value('authors', 'authors')
    description = _fetch_value('description', 'description')
    logo        = _fetch_value('logo', 'logo')
    credits     = _fetch_value('credits', 'credits')
    information = _fetch_value('information', 'information')

    legacy_mode = safe_info.get('dialog_mode') if safe_info else None
    effective_mode = dialog_mode or AboutDialogMode.CLASSIC
    if legacy_mode is not None:
        if isinstance(legacy_mode, AboutDialogMode):
            effective_mode = legacy_mode
        else:
            try:
                effective_mode = AboutDialogMode[str(legacy_mode)]
            except Exception:
                logger.debug("Unsupported legacy dialog_mode value: %s", legacy_mode)

    def _normalize_size(size_spec):
        width = 320
        height = 240
        if size_spec is None and safe_info.get('size'):
            size_spec = safe_info.get('size')
        if isinstance(size_spec, dict):
            width = size_spec.get('width', width)
            if 'width' not in size_spec:
                if 'column' in size_spec:
                    width = size_spec['column']
                elif 'columns' in size_spec:
                    width = size_spec['columns']
            height = size_spec.get('height', height)
            if 'height' not in size_spec:
                if 'lines' in size_spec:
                    height = size_spec['lines']
                elif 'rows' in size_spec:
                    height = size_spec['rows']
        elif isinstance(size_spec, (list, tuple)):
            if len(size_spec) > 0 and size_spec[0] is not None:
                width = size_spec[0]
            if len(size_spec) > 1 and size_spec[1] is not None:
                height = size_spec[1]
        elif size_spec is not None:
            logger.debug("Unsupported size specification type: %s", type(size_spec))
        try:
            width = int(width)
            height = int(height)
        except Exception:
            width, height = 320, 240
        return width, height

    dlg = None
    try:
        factory = yui.YUI.widgetFactory()
        dlg = factory.createPopupDialog()
        title = _("About") + (" " + name if name else "")
        old_title = _push_app_title(title)
        root_vbox = factory.createVBox(dlg)

        # Optional MinSize wrapper (accepts {'width','height'} in pixels)
        content_parent = root_vbox
        width_hint, height_hint = _normalize_size(size if size is not None else None)
        if width_hint > 0 and height_hint > 0:
            try:
                content_parent = factory.createMinSize(root_vbox, int(width_hint), int(height_hint))
            except Exception as exc:
                logger.debug("Unable to apply size hint (%s, %s): %s", width_hint, height_hint, exc)

        vbox = factory.createVBox(content_parent)

        logger.debug(
            "Opening AboutDialog name='%s' mode=%s",
            name or "",
            getattr(effective_mode, "name", effective_mode),
        )

        # Header block (logo + labels)
        header = factory.createHBox(vbox)
        if logo:
            try:
                factory.createImage(header, logo)
                factory.createSpacing(header, 8)
            except Exception as exc:
                logger.debug("Unable to load logo '%s': %s", logo, exc)
        labels = factory.createVBox(header)
        if name:
            factory.createLabel(labels, name)
        if version:
            factory.createLabel(labels, version)
        if license_txt:
            factory.createLabel(labels, license_txt)

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
        tab_widget = None
        tab_content_updater = None

        tab_sections = []
        if description:
            tab_sections.append((_('Description'), description))
        if authors:
            tab_sections.append((_('Authors'), authors))
        if information:
            tab_sections.append((_('Information'), information))
        if credits:
            tab_sections.append((_('Credits'), credits))

        use_tabbed = (effective_mode == AboutDialogMode.TABBED)
        tab_text_widget = None

        if use_tabbed:
            if not tab_sections:
                logger.debug("Tabbed mode requested but there are no sections; falling back to classic mode.")
                use_tabbed = False
            else:
                try:
                    tabs_box = factory.createVBox(vbox)
                    tab_widget = factory.createDumbTab(tabs_box)
                    tab_widget.setNotify(True)
                    content_holder = factory.createReplacePoint(tabs_box)
                    tab_text_widget = _add_richtext(content_holder, "")
                    try:
                        content_holder.showChild()
                    except Exception as exc:
                        logger.debug("Unable to show tab content immediately: %s", exc)
                    added_items = []
                    for section_title, section_value in tab_sections:
                        item = YItem(section_title)
                        item.setData(section_value)
                        tab_widget.addItem(item)
                        added_items.append(item)
                    if not added_items:
                        logger.debug("No tab items added; reverting to classic mode.")
                        use_tabbed = False
                        tab_widget = None
                    else:
                        try:
                            tab_widget.selectItem(added_items[0], True)
                        except Exception as exc:
                            logger.debug("Unable to preselect first tab: %s", exc)

                        def _update_tab_content():
                            current_item = tab_widget.selectedItem()
                            payload = ""
                            if current_item is not None:
                                payload = current_item.data() or ""
                            if tab_text_widget is not None:
                                tab_text_widget.setValue(payload)

                        _update_tab_content()
                        tab_content_updater = _update_tab_content
                except Exception as exc:
                    logger.exception("Failed to initialize tabbed AboutDialog: %s", exc)
                    use_tabbed = False
                    tab_widget = None
                    tab_content_updater = None

        if not use_tabbed:
            if description:
                _add_richtext(vbox, description)
            if authors:
                factory.createHeading(vbox, _("Authors"))
                _add_richtext(vbox, authors)

            if information or credits:
                button_row = factory.createHBox(vbox)
                if information:
                    info_btn = factory.createPushButton(button_row, _("&Info"))
                if credits:
                    credits_btn = factory.createPushButton(button_row, _("&Credits"))
            else:
                button_row = None

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
                logger.debug("AboutDialog closing due to event type %s", et)
                break
            if et != yui.YEventType.WidgetEvent:
                continue
            widget = ev.widget()
            if widget == close_btn:
                logger.debug("AboutDialog close button activated")
                break
            if tab_widget and widget == tab_widget:
                if tab_content_updater:
                    tab_content_updater()
                continue
            if info_btn and widget == info_btn:
                logger.debug("AboutDialog information button activated")
                msgBox({"title": _("Information"), "text": information or "", "richtext": True})
                continue
            if credits_btn and widget == credits_btn:
                logger.debug("AboutDialog credits button activated")
                msgBox({"title": _("Credits"), "text": credits or "", "richtext": True})
                continue

            logger.debug("Unhandled widget event from %s", getattr(widget, 'widgetClass', lambda: 'unknown')())

        dlg.destroy()
    finally:
        if dlg is not None:
            try:
                dlg.destroy()
            except Exception:
                pass
        _restore_app_title(old_title)
