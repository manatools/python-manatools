# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.gtk contains all gtk backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
'''
import logging
import locale
from gi.repository import Gtk
from ...yui_common import *


def _locale_date_order():
    try:
        locale.setlocale(locale.LC_TIME, '')
    except Exception:
        pass
    try:
        fmt = locale.nl_langinfo(locale.D_FMT)
    except Exception:
        fmt = '%Y-%m-%d'
    fmt = fmt or '%Y-%m-%d'
    order = []
    i = 0
    while i < len(fmt):
        if fmt[i] == '%':
            i += 1
            if i < len(fmt):
                c = fmt[i]
                if c in ('Y', 'y'):
                    order.append('Y')
                elif c in ('m', 'b', 'B'):
                    order.append('M')
                elif c in ('d', 'e'):
                    order.append('D')
        i += 1
    # ensure Y, M, D present
    for x in ['Y', 'M', 'D']:
        if x not in order:
            order.append(x)
    return order[:3]


class YDateFieldGtk(YWidget):
    """GTK backend YDateField implemented with three SpinButtons ordered per system locale date order.
    value()/setValue() use ISO format YYYY-MM-DD. No change events posted.
    """
    def __init__(self, parent=None, label: str = ""):
        super().__init__(parent)
        self._label = label or ""
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        try:
            self._logger.debug("%s.__init__ label=%s", self.__class__.__name__, self._label)
        except Exception:
            pass
        self._y = 2000
        self._m = 1
        self._d = 1
        self._order = _locale_date_order()

    def widgetClass(self):
        return "YDateField"

    def value(self) -> str:
        try:
            return f"{self._y:04d}-{self._m:02d}-{self._d:02d}"
        except Exception:
            return ""

    def setValue(self, datestr: str):
        try:
            y, m, d = [int(p) for p in str(datestr).split('-')]
        except Exception:
            return
        y = max(1, min(9999, y))
        m = max(1, min(12, m))
        dmax = self._days_in_month(y, m)
        d = max(1, min(dmax, d))
        self._y, self._m, self._d = y, m, d
        self._sync_spins()

    def _days_in_month(self, y, m):
        if m in (1,3,5,7,8,10,12):
            return 31
        if m in (4,6,9,11):
            return 30
        # February
        leap = (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0))
        return 29 if leap else 28

    def _sync_spins(self):
        if getattr(self, '_spin_y', None):
            try: self._spin_y.set_value(self._y) 
            except Exception: pass
        if getattr(self, '_spin_m', None):
            try: 
                self._spin_m.set_value(self._m)
            except Exception: pass
        if getattr(self, '_spin_d', None):
            try:
                self._spin_d.get_adjustment().set_upper(self._days_in_month(self._y, self._m))
                self._spin_d.set_value(self._d)
            except Exception: pass

    def _create_backend_widget(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        if self._label:
            lbl = Gtk.Label.new(self._label)
            lbl.set_xalign(0.0)
            box.append(lbl)
            self._label_widget = lbl

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.append(row)

        # Create spins
        self._spin_y = Gtk.SpinButton.new_with_range(1, 9999, 1)
        self._spin_y.set_width_chars(4)
        self._spin_m = Gtk.SpinButton.new_with_range(1, 12, 1)
        self._spin_m.set_width_chars(2)
        self._spin_d = Gtk.SpinButton.new_with_range(1, 31, 1)
        self._spin_d.set_width_chars(2)

        # Initialize default date
        self._sync_spins()

        # Connect to maintain boundaries but do not post events
        def on_y_changed(spin):
            try:
                self._y = int(spin.get_value())
                # re-clamp day for new year (leap)
                dmax = self._days_in_month(self._y, self._m)
                if self._d > dmax:
                    self._d = dmax
                    self._spin_d.set_value(self._d)
            except Exception:
                pass
        def on_m_changed(spin):
            try:
                self._m = int(spin.get_value())
                dmax = self._days_in_month(self._y, self._m)
                self._spin_d.get_adjustment().set_upper(dmax)
                if self._d > dmax:
                    self._d = dmax
                    self._spin_d.set_value(self._d)
            except Exception:
                pass
        def on_d_changed(spin):
            try:
                self._d = int(spin.get_value())
            except Exception:
                pass

        self._spin_y.connect('value-changed', on_y_changed)
        self._spin_m.connect('value-changed', on_m_changed)
        self._spin_d.connect('value-changed', on_d_changed)

        # Order per locale
        for part in self._order:
            if part == 'Y':
                row.append(self._spin_y)
            elif part == 'M':
                row.append(self._spin_m)
            else:
                row.append(self._spin_d)

        self._backend_widget = box
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        try:
            for w in (getattr(self, '_spin_y', None), getattr(self, '_spin_m', None), getattr(self, '_spin_d', None), getattr(self, '_label_widget', None)):
                if w is not None:
                    w.set_sensitive(bool(enabled))
        except Exception:
            pass
