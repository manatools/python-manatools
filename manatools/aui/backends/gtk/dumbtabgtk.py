# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.gtk contains all GTK backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
'''
'''
GTK4 backend DumbTab (tab bar + single content area)

Implements a tab bar using Gtk.Notebook with scrollable tabs (scroll arrows appear
when there are more tabs than space allows, matching Qt QTabBar behaviour).
The Notebook pages are empty placeholders; actual content lives in _content below.

This is a YSelectionWidget: it manages items, single selection, and
emits WidgetEvent(Activated) when the active tab changes.
'''
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
import logging
from ...yui_common import *

class YDumbTabGtk(YSelectionWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        self._box = None
        self._notebook = None   # Gtk.Notebook — provides scrollable classic tab bar
        self._content = None    # Gtk.Box   — actual child (ReplacePoint) lives here
        self._inhibit_signal = False  # guard against re-entrant switch-page signals
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)

    def widgetClass(self):
        return "YDumbTab"

    def _create_backend_widget(self):
        try:
            self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

            # Gtk.Notebook gives classic tab handles + scroll arrows (like Qt QTabBar).
            self._notebook = Gtk.Notebook()
            self._notebook.set_scrollable(True)   # ← scroll arrows when tabs overflow
            self._notebook.set_show_border(False)  # remove frame around (empty) content area
            self._notebook.set_hexpand(True)
            self._notebook.set_vexpand(False)

            # Actual child content goes here, below the tab bar
            self._content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            self._content.set_hexpand(True)
            self._content.set_vexpand(True)

            self._box.append(self._notebook)
            self._box.append(self._content)

            # Populate tab pages from items already in the model
            active_idx = -1
            for idx, it in enumerate(self._items):
                self._append_notebook_page(it.label())
                if it.selected():
                    active_idx = idx
            if active_idx < 0 and len(self._items) > 0:
                active_idx = 0
                try:
                    self._items[0].setSelected(True)
                except Exception:
                    pass
            if active_idx >= 0:
                self._inhibit_signal = True
                try:
                    self._notebook.set_current_page(active_idx)
                except Exception:
                    pass
                self._inhibit_signal = False
                self._selected_items = [self._items[active_idx]]

            # Attach pre-existing child content (e.g. a ReplacePoint)
            try:
                if self.hasChildren():
                    ch = self.firstChild()
                    if ch is not None:
                        w = ch.get_backend_widget()
                        try:
                            self._content.append(w)
                        except Exception:
                            pass
                        try:
                            self._logger.debug(
                                "YDumbTabGtk._create_backend_widget: attached pre-existing child %s",
                                ch.widgetClass())
                        except Exception:
                            pass
            except Exception:
                pass

            self._box.set_sensitive(self._enabled)
            self._backend_widget = self._box

            self._notebook.connect('switch-page', self._on_notebook_changed)

            try:
                self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
            except Exception:
                pass
        except Exception:
            try:
                self._logger.exception("YDumbTabGtk _create_backend_widget failed")
            except Exception:
                pass

    # ── internal helpers ───────────────────────────────────────────────────

    def _append_notebook_page(self, label_text):
        """Add a single empty placeholder page with the given label text."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        # The page height should be 0; set_size_request keeps it minimal
        page.set_size_request(-1, 0)
        tab_label = Gtk.Label(label=label_text)
        self._notebook.append_page(page, tab_label)

    # ── YWidget interface ──────────────────────────────────────────────────

    def addChild(self, child):
        """Accept only a single child; attach its backend into the content area."""
        if self.hasChildren():
            raise YUIInvalidWidgetException("YDumbTab can only have one child")
        super().addChild(child)
        try:
            if self._content is not None:
                w = child.get_backend_widget()
                self._content.append(w)
                try:
                    self._logger.debug("YDumbTabGtk.addChild: attached %s into content",
                                       child.widgetClass())
                except Exception:
                    pass
        except Exception:
            try:
                self._logger.exception("YDumbTabGtk.addChild failed")
            except Exception:
                pass

    def deleteAllItems(self):
        super().deleteAllItems()
        if self._notebook is None:
            return
        try:
            self._inhibit_signal = True
            while self._notebook.get_n_pages() > 0:
                self._notebook.remove_page(0)
        except Exception:
            try:
                self._logger.exception("YDumbTabGtk.deleteAllItems failed")
            except Exception:
                pass
        finally:
            self._inhibit_signal = False

    def addItem(self, item):
        super().addItem(item)
        if self._notebook is None:
            return
        try:
            self._append_notebook_page(item.label())
            if item.selected():
                self._inhibit_signal = True
                try:
                    self._notebook.set_current_page(self._notebook.get_n_pages() - 1)
                except Exception:
                    pass
                self._inhibit_signal = False
            self._sync_selection_from_notebook()
        except Exception:
            try:
                self._logger.exception("YDumbTabGtk.addItem failed")
            except Exception:
                pass

    def selectItem(self, item, selected=True):
        if not selected:
            return
        try:
            target_idx = None
            for i, it in enumerate(self._items):
                if it is item:
                    target_idx = i
                    break
            if target_idx is None:
                return
            if self._notebook is not None:
                self._inhibit_signal = True
                try:
                    self._notebook.set_current_page(target_idx)
                except Exception:
                    pass
                self._inhibit_signal = False
            for it in self._items:
                it.setSelected(False)
            item.setSelected(True)
            self._selected_items = [item]
        except Exception:
            try:
                self._logger.exception("YDumbTabGtk.selectItem failed")
            except Exception:
                pass

    # ── signal handler ─────────────────────────────────────────────────────

    def _on_notebook_changed(self, notebook, page_widget, page_num):
        if self._inhibit_signal:
            return
        try:
            index = page_num
            if 0 <= index < len(self._items):
                for i, it in enumerate(self._items):
                    try:
                        it.setSelected(i == index)
                    except Exception:
                        pass
                self._selected_items = [self._items[index]]
            else:
                self._selected_items = []
            if self.notify():
                dlg = self.findDialog()
                if dlg is not None:
                    dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
        except Exception:
            try:
                self._logger.exception("YDumbTabGtk._on_notebook_changed failed")
            except Exception:
                pass

    def _sync_selection_from_notebook(self):
        if self._notebook is None:
            self._selected_items = []
            return
        try:
            idx = self._notebook.get_current_page()
            if 0 <= idx < len(self._items):
                self._selected_items = [self._items[idx]]
            else:
                self._selected_items = []
        except Exception:
            self._selected_items = []

