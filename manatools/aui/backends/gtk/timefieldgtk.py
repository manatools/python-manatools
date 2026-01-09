# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.gtk contains all gtk backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
'''
import logging
import datetime
from gi.repository import Gtk
from ...yui_common import *


class YTimeFieldGtk(YWidget):
    """GTK backend YTimeField implemented as an Entry + MenuButton Popover with three SpinButtons (H/M/S).
    value()/setValue() use HH:MM:SS. No change events posted.
    """
    def __init__(self, parent=None, label: str = ""):
        super().__init__(parent)
        self._label = label or ""
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        self._time = datetime.time(0, 0, 0)
        self._popover = None
        self._pending = None  # pending datetime.time (not used when updating live)
        self._spin_h = None
        self._spin_m = None
        self._spin_s = None
        self.setStretchable(YUIDimension.YD_HORIZ, False)
        self.setStretchable(YUIDimension.YD_VERT, False)

    def widgetClass(self):
        return "YTimeField"

    def value(self) -> str:
        try:
            t = getattr(self, '_time', None)
            if t is None:
                return ''
            return f"{t.hour:02d}:{t.minute:02d}:{t.second:02d}"
        except Exception:
            return ""

    def setValue(self, timestr: str):
        try:
            parts = str(timestr).split(':')
            if len(parts) != 3:
                return
            h, m, s = [int(p) for p in parts]
            h = max(0, min(23, h))
            m = max(0, min(59, m))
            s = max(0, min(59, s))
            self._time = datetime.time(h, m, s)
            self._update_display()
            # Keep spin buttons in sync with the current time
            try:
                self._sync_spins_from_time()
            except Exception:
                self._logger.exception("setValue: failed to sync spins from time")
        except Exception as e:
            self._logger.exception("setValue failed: %s", e)

    def _update_display(self):
        try:
            if getattr(self, '_entry', None) is not None:
                t = getattr(self, '_time', None)
                txt = '' if t is None else f"{t.hour:02d}:{t.minute:02d}:{t.second:02d}"
                self._entry.set_text(txt)
        except Exception:
            self._logger.exception("_update_display failed")
            pass

    def _sync_spins_from_time(self):
        try:
            if self._spin_h is not None:
                self._spin_h.set_value(self._time.hour)
            if self._spin_m is not None:
                self._spin_m.set_value(self._time.minute)
            if self._spin_s is not None:
                self._spin_s.set_value(self._time.second)
        except Exception:
            self._logger.exception("_sync_spins_from_time failed")

    def _create_backend_widget(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        if self._label:
            lbl = Gtk.Label(label=self._label)
            lbl.set_xalign(0.0)
            outer.append(lbl)
            self._label_widget = lbl

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        entry = Gtk.Entry()
        # Default: do not expand horizontally unless the widget was created stretchable
        entry.set_hexpand(bool(self.stretchable(YUIDimension.YD_HORIZ)))
        row.append(entry)
        self._entry = entry

        btn = Gtk.MenuButton()
        row.append(btn)

        outer.append(row)

        pop = Gtk.Popover()
        grid = Gtk.Grid(column_spacing=6, row_spacing=6)

        adj_h = Gtk.Adjustment(lower=0, upper=23, step_increment=1, page_increment=5)
        spin_h = Gtk.SpinButton(adjustment=adj_h)
        adj_m = Gtk.Adjustment(lower=0, upper=59, step_increment=1, page_increment=5)
        spin_m = Gtk.SpinButton(adjustment=adj_m)
        adj_s = Gtk.Adjustment(lower=0, upper=59, step_increment=1, page_increment=5)
        spin_s = Gtk.SpinButton(adjustment=adj_s)
        self._spin_h, self._spin_m, self._spin_s = spin_h, spin_m, spin_s
        # Initialize spin buttons to the current time so popover opens consistent with entry
        try:
            self._sync_spins_from_time()
        except Exception:
            self._logger.exception("init: failed to sync spins from time")

        grid.attach(Gtk.Label(label="H:"), 0, 0, 1, 1)
        grid.attach(spin_h, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="M:"), 0, 1, 1, 1)
        grid.attach(spin_m, 1, 1, 1, 1)
        grid.attach(Gtk.Label(label="S:"), 0, 2, 1, 1)
        grid.attach(spin_s, 1, 2, 1, 1)

        pop.set_child(grid)
        btn.set_popover(pop)

        def _sync_spins():
            try:
                self._sync_spins_from_time()
            except Exception:
                self._logger.exception("_sync_spins failed")

        def _on_spin_changed(*_):
            try:
                h = int(spin_h.get_value())
                m = int(spin_m.get_value())
                s = int(spin_s.get_value())
                self._time = datetime.time(max(0, min(23, h)), max(0, min(59, m)), max(0, min(59, s)))
                self._logger.debug("spin commit: %02d:%02d:%02d", self._time.hour, self._time.minute, self._time.second)
                self._update_display()
            except Exception:
                self._logger.exception("spin changed handler failed")

        for sp in (spin_h, spin_m, spin_s):
            try:
                sp.connect('value-changed', _on_spin_changed)
            except Exception:
                self._logger.exception("couldn't connect spin value-changed")

        def _on_btn_activate(*_):
            try:
                self._pending = None
                _sync_spins()
            except Exception:
                self._logger.exception("menu button activate handler failed")
        try:
            # Gtk.MenuButton uses 'activate' in GTK4
            btn.connect('activate', _on_btn_activate)
        except Exception:
            self._logger.exception("couldn't connect button activate")

        # No need to commit on close as we update live on spin changes

        def _on_entry_activate(e):
            try:
                parts = str(e.get_text()).strip().split(':')
                if len(parts) == 3:
                    h, m, s = [int(p) for p in parts]
                    h = max(0, min(23, h))
                    m = max(0, min(59, m))
                    s = max(0, min(59, s))
                    self._time = datetime.time(h, m, s)
                    self._logger.debug("entry commit: %02d:%02d:%02d", h, m, s)
                    self._update_display()
                    # Sync spins if popover is open or later when it opens
                    self._sync_spins_from_time()
            except Exception as ex:
                self._logger.exception("entry activate parse failed: %s", ex)
        try:
            entry.connect('activate', _on_entry_activate)
        except Exception:
            self._logger.exception("couldn't connect entry activate")
        try:
            # Commit on focus loss in GTK4 via notify::has-focus
            def _on_entry_focus_notify(e, pspec):
                try:
                    if not e.has_focus():
                        _on_entry_activate(e)
                except Exception:
                    self._logger.exception("entry focus notify failed")
            entry.connect('notify::has-focus', _on_entry_focus_notify)
        except Exception:
            self._logger.exception("couldn't connect entry focus notify")

        # Ensure spins are in sync at startup
        try:
            self._sync_spins_from_time()
        except Exception:
            self._logger.exception("startup: failed to sync spins from time")
        self._update_display()
        self._backend_widget = outer
        self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())

    def _set_backend_enabled(self, enabled):
        try:
            for w in (getattr(self, '_entry', None), getattr(self, '_label_widget', None)):
                if w is not None:
                    w.set_sensitive(bool(enabled))
        except Exception:
            pass
