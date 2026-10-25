# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains all Qt backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''
from PySide6 import QtWidgets, QtGui, QtCore
import os
import logging
from ...yui_common import *


__all__ = ["_resolve_icon", "_install_context_menu_filter", "_open_context_menu"]

def _resolve_icon(icon_name):
    """Resolve an icon name to a QtGui.QIcon or None.

    - If icon_name is an existing absolute or relative path -> load from path.
    - If icon_name contains a path separator or exists on filesystem -> treat as path.
    - Otherwise strip extension (if any) and try QIcon.fromTheme, then fallback to QIcon(name).
    """
    try:
        if not icon_name:
            return None
        logger = logging.getLogger(f"manatools.aui.qt.common")
        # If icon_name looks like a filesystem path (absolute or contains a
        # path separator), prefer loading from disk. If it has no
        # extension, also try the same path with a .png suffix to help
        # debugging/test cases where a directory+basename is provided.
        # Only treat as a filesystem path when the name is absolute or contains
        # a path separator.  Bare names like "isodumper" are theme-icon names
        # and must NOT be probed on disk — the CWD may contain a launcher
        # script with the same name (e.g. isodumper/isodumper), which would
        # cause QIcon to silently load a binary file instead of the theme icon.
        is_file_path = os.path.isabs(icon_name) or os.sep in icon_name
        try:
            if is_file_path:
                if os.path.isfile(icon_name):
                    return QtGui.QIcon(icon_name)
                # no extension → also try .png suffix
                base, ext = os.path.splitext(icon_name)
                if not ext:
                    png_candidate = icon_name + '.png'
                    if os.path.isfile(png_candidate):
                        logger.debug("Resolved icon %r to %r", icon_name, png_candidate)
                        return QtGui.QIcon(png_candidate)
                # not found on filesystem: fall through to theme lookup
            else:
                # Bare name with an explicit extension can still be a relative
                # file reference (e.g. "logo.png" in the same directory).
                # Bare names without an extension are always theme-icon names.
                if "." in icon_name and os.path.isfile(icon_name):
                    logger.debug("Resolved icon %r to relative filesystem path", icon_name)
                    return QtGui.QIcon(icon_name)
        except Exception:
            pass
        base = icon_name
        try:
            if "." in base:
                base = os.path.splitext(base)[0]
        except Exception:
            pass
        try:
            logger.debug("Trying to resolve icon %r via QIcon.fromTheme(%r)", icon_name, base)
            ico = QtGui.QIcon.fromTheme(base)
            if ico and not ico.isNull():
                logger.debug("Resolved icon %r to theme icon %r", icon_name, base)
                return ico
        except Exception:
            pass
        try:
            ico = QtGui.QIcon(icon_name)
            if ico and not ico.isNull():
                logger.debug("Resolved icon %r to QIcon(%r)", icon_name, icon_name)
                return ico
        except Exception:
            pass
    except Exception:
        pass
    return None


class _ContextMenuFilter(QtCore.QObject):
    """Turn a right-click or the Menu key on an item view into ContextMenuActivated.

    Installed on the view (keyboard requests go to the focus widget) and on
    its viewport (mouse requests). Does nothing unless the owner has
    notifyContextMenu() set, so widgets need no setter override.
    """
    def __init__(self, owner, view):
        super().__init__(view)
        self._owner = owner
        self._view = view
        self._logger = logging.getLogger("manatools.aui.qt.common")

    def eventFilter(self, obj, event):
        etype = event.type()
        if etype not in (QtCore.QEvent.Type.ContextMenu, QtCore.QEvent.Type.MouseButtonPress):
            return False
        owner = self._owner
        if not owner.notifyContextMenu():
            return False
        view = self._view
        if etype == QtCore.QEvent.Type.MouseButtonPress:
            # Item views toggle the row on right-press in MultiSelection mode,
            # which would break "right-click inside a selection keeps it".
            # Selection is handled on the ContextMenu event instead.
            if event.button() == QtCore.Qt.MouseButton.RightButton and obj is view.viewport():
                view.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
                return True
            return False
        try:
            if event.reason() == QtGui.QContextMenuEvent.Reason.Mouse:
                pos = event.pos() if obj is view.viewport() else view.viewport().mapFrom(view, event.pos())
                index = view.indexAt(pos)
                global_pos = event.globalPos()
            else:
                index = view.currentIndex()
                rect = view.visualRect(index) if index.isValid() else view.viewport().rect()
                global_pos = view.viewport().mapToGlobal(rect.bottomLeft() if index.isValid() else rect.center())
            # Right-click on an unselected row selects only that row first, so
            # the handler can rely on selectedItem(); inside a selection keep it.
            sel = view.selectionModel()
            if index.isValid() and sel is not None and not sel.isRowSelected(index.row(), index.parent()):
                sel.setCurrentIndex(index, QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
                                    | QtCore.QItemSelectionModel.SelectionFlag.Rows)
            dlg = owner.findDialog()
            if dlg is None:
                return True
            dlg._context_menu_source = owner
            dlg._context_menu_pos = global_pos
            dlg._post_event(YWidgetEvent(owner, YEventReason.ContextMenuActivated))
        except Exception:
            self._logger.exception("context menu request failed")
        return True


def _install_context_menu_filter(owner, view):
    """Route context menu requests on the QAbstractItemView view to owner."""
    flt = _ContextMenuFilter(owner, view)
    view.installEventFilter(flt)
    view.viewport().installEventFilter(flt)
    return flt


def _add_context_menu_items(qmenu, root, items, top_items, dlg, source):
    for item in items:
        if not item.visible():
            continue
        if item.isSeparator():
            qmenu.addSeparator()
            continue
        icon = _resolve_icon(item.iconName()) if item.iconName() else None
        if item.isMenu():
            sub = qmenu.addMenu(item.label())
            if icon is not None:
                sub.setIcon(icon)
            sub.menuAction().setEnabled(item.enabled())
            _add_context_menu_items(sub, root, item._children, top_items, dlg, source)
            continue
        act = qmenu.addAction(item.label())
        if icon is not None:
            act.setIcon(icon)
        act.setEnabled(item.enabled())

        def on_triggered(_checked=False, item=item):
            root._picked = True
            dlg._post_event(YMenuEvent(item=item, id=context_menu_item_path(item, top_items), widget=source))
        act.triggered.connect(on_triggered)


def _open_context_menu(dlg, items) -> bool:
    """Pop up a QMenu for the pending context request of dlg (non-blocking).

    The menu is built from the current item state (a snapshot), so the app may
    change shared YMenuItem objects freely between openings.
    """
    source = getattr(dlg, "_context_menu_source", None)
    if source is None:
        return False
    top_items = context_menu_items(items)
    if not has_selectable_item(top_items):
        return False
    pos = getattr(dlg, "_context_menu_pos", None) or QtGui.QCursor.pos()
    dlg._context_menu_source = None
    dlg._context_menu_pos = None

    old = getattr(dlg, "_context_menu", None)
    if old is not None:
        old._picked = True  # replaced, not dismissed
        old.close()
    view = source.get_backend_widget()
    qmenu = QtWidgets.QMenu(view)
    qmenu._picked = False
    _add_context_menu_items(qmenu, qmenu, top_items, top_items, dlg, source)

    def on_hide():
        # aboutToHide fires before the action's triggered(): decide on the
        # next loop iteration, once a pick had the chance to flag the menu.
        def finish():
            if dlg._context_menu is qmenu:
                dlg._context_menu = None
            if not qmenu._picked:
                dlg._post_event(YWidgetEvent(source, YEventReason.ContextMenuCancelled))
            qmenu.deleteLater()
        QtCore.QTimer.singleShot(0, finish)
    qmenu.aboutToHide.connect(on_hide)
    dlg._context_menu = qmenu
    qmenu.popup(pos)
    return True
