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
import datetime
from gi.repository import Gtk, GLib
from ...yui_common import *


class YDateFieldGtk(YWidget):
    """GTK backend YDateField implemented as a compact button with popup Gtk.Calendar.
    value()/setValue() use ISO format YYYY-MM-DD. No change events posted.
    """
    def __init__(self, parent=None, label: str = ""):
        super().__init__(parent)
        self._label = label or ""
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        # store current value as a date object (use only the date portion)
        self._date = datetime.date(2000, 1, 1)
        self._calendar = None
        self._menu_btn = None
        self._date_label = None
        self._popover = None
        self._locale_date_fmt = None

    def widgetClass(self):
        return "YDateField"

    def value(self) -> str:
        try:
            d = getattr(self, '_date', None)
            if d is None:
                return ''
            return d.isoformat()
        except Exception:
            return ""

    def setValue(self, datestr: str):
        try:
            # accept ISO-like YYYY-MM-DD
            parts = str(datestr).split('-')
            if len(parts) != 3:
                return
            y, m, d = [int(p) for p in parts]
        except Exception:
            return
        try:
            y = max(1, min(9999, y))
            m = max(1, min(12, m))
            dmax = self._days_in_month(y, m)
            d = max(1, min(dmax, d))
            newdate = datetime.date(y, m, d)
        except Exception:
            return
        self._set_date(newdate)

    def _get_locale_date_fmt(self):
        if getattr(self, '_locale_date_fmt', None):
            return self._locale_date_fmt
        try:
            try:
                locale.setlocale(locale.LC_TIME, '')
            except Exception:
                pass
            fmt = locale.nl_langinfo(locale.D_FMT)
        except Exception:
            fmt = '%Y-%m-%d'
        fmt = fmt or '%Y-%m-%d'
        self._locale_date_fmt = fmt
        return fmt

    def _days_in_month(self, y, m):
        if m in (1,3,5,7,8,10,12):
            return 31
        if m in (4,6,9,11):
            return 30
        # February
        leap = (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0))
        return 29 if leap else 28

    def _create_backend_widget(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        if self._label:
            lbl = Gtk.Label.new(self._label)
            lbl.set_xalign(0.0)
            box.append(lbl)
            self._label_widget = lbl

        # Horizontal DateEdit: entry + calendar button
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._date_entry = Gtk.Entry()
        self._date_entry.set_hexpand(True)
        # placeholder in system locale format
        try:
            fmt = self._get_locale_date_fmt()
            sample = datetime.date(2000, 1, 15).strftime(fmt)
        except Exception:
            sample = "YYYY-MM-DD"
        self._date_entry.set_placeholder_text(sample)
        row.append(self._date_entry)

        # MenuButton styled as dropdown
        self._cal_button = Gtk.MenuButton()
        try:
            img = Gtk.Image.new_from_icon_name("open-menu-symbolic")
            self._cal_button.set_child(img)
        except Exception:
            try:
                self._cal_button.set_label("▾")
            except Exception:
                pass
        row.append(self._cal_button)

        # Popover with Calendar
        self._popover = Gtk.Popover()
        cal = Gtk.Calendar()

        # GLib.DateTime uses 1-based months (January=1)
        gdate = GLib.DateTime.new_utc(self._date.year, self._date.month, self._date.day, 0, 0, 0)
        # Use set_date() for GTK 4.20+
        try:
            self._calendar.set_date(gdate)
        except Exception as e:
            # Fall back to select_day() if set_date() fails unexpectedly
            self._logger.debug("Failed to set_date() on calendar: %s", e)
            try:
                self._calendar.select_day(gdate)
            except Exception:
                self._logger.exception("Failed to initialize calendar select_day()")

        # Entry handlers: parse and commit to value
        def _parse_and_set(datestr):
            try:
                parts = str(datestr).strip()
                if not parts:
                    return False
                y = m = d = None
                if '-' in parts:
                    ymd = parts.split('-')
                    if len(ymd) == 3 and all(p.isdigit() for p in ymd):
                        y, m, d = [int(p) for p in ymd]
                if y is None:
                    try:
                        fmt = self._get_locale_date_fmt()
                        dt = datetime.datetime.strptime(parts, fmt)
                        y, m, d = dt.year, dt.month, dt.day
                    except Exception:
                        return False
            except Exception:
                return False
            y = max(1, min(9999, y))
            m = max(1, min(12, m))
            dmax = self._days_in_month(y, m)
            d = max(1, min(dmax, d))
            try:
                newdate = datetime.date(y, m, d)
            except Exception:
                return False
            self._date = newdate
            # GLib.DateTime uses 1-based months (January=1)
            gdate = GLib.DateTime.new_utc(self._date.year, self._date.month, self._date.day, 0, 0, 0)
            # Use set_date() for GTK 4.20+
            try:
                self._calendar.set_date(gdate)
            except Exception as e:
                # Fall back to select_day() if set_date() fails unexpectedly
                self._logger.debug("Failed to set_date() on calendar: %s", e)
                try:
                    self._calendar.select_day(gdate)
                except Exception:
                    self._logger.exception("Failed to initialize calendar select_day()")
            self._logger.debug("entry commit: %04d-%02d-%02d", y, m, d)
            return True

        def _on_entry_activate(entry):
            txt = entry.get_text()
            _parse_and_set(txt)

        try:
            self._date_entry.connect('activate', _on_entry_activate)
            self._date_entry.connect('changed', _on_entry_activate)
        except Exception:
            self._logger.exception("Failed to connect entry activate")

        # Calendar handlers: pending selection, commit on popover close
        def _refresh_from_calendar(calendar):
            try:                
                try:
                    y = calendar.get_year()
                    m = calendar.get_month()
                    d = calendar.get_day()
                except Exception:
                    self._logger.debug("calendar refresh: get_year/month/day failed (since gtk 4.14)")
                    try:
                        gdatetime = calendar.get_date()    
                        y = gdatetime.get_year()
                        m = gdatetime.get_month()
                        d = gdatetime.get_day_of_month()
                    except Exception:
                        self._logger.exception("calendar refresh: get_date() failed")
                        return
                # calendar.get_date() returns month as 0-based
                y, m, d = int(y), int(m) + 1, int(d)
                try:
                    pending = datetime.date(y, m, d)
                except Exception:
                    pending = None
                    self._logger.debug("calendar refresh: invalid date %04d-%02d-%02d", y, m, d)
                try:
                    if pending is not None:
                        self._logger.debug("calendar select pending=%04d-%02d-%02d", pending.year, pending.month, pending.day)
                        self._set_date(pending)                        
                except Exception:
                    self._logger.exception("Failed to set date from calendar")
            except Exception:
                self._logger.exception("Failed in _refresh_from_calendar")

        try:
            cal.connect("day-selected", _refresh_from_calendar)
        except Exception:
            self._logger.exception("Failed to connect day-selected")
        try:
            cal.connect("next-month", _refresh_from_calendar)
        except Exception:
            self._logger.exception("Failed to connect next-month")
        try:
            cal.connect("prev-month", _refresh_from_calendar)
        except Exception:
            self._logger.exception("Failed to connect prev-month")
        try:
            cal.connect("next-year", _refresh_from_calendar)
        except Exception:
            self._logger.exception("Failed to connect next-year")
        try:
            cal.connect("prev-year", _refresh_from_calendar)
        except Exception:
            self._logger.exception("Failed to connect prev-year")

        # Sync calendar to current value when popover opens
        try:
            def _on_button_clicked(b):
                try:
                    self._logger.debug("popover open: sync %04d-%02d-%02d", self._date.year, self._date.month, self._date.day)
                    cal.set_year(self._date.year)
                    cal.set_month(self._date.month - 1)
                    cal.set_day(self._date.day)                    
                except Exception:
                    self._logger.exception("Failed to sync calendar on popover open")
            self._cal_button.connect('activate', _on_button_clicked)
        except Exception:
            self._logger.exception("Failed to connect button activate")

        # Put calendar inside a box with margins inside the popover
        popbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        try:
            popbox.set_margin_top(6)
            popbox.set_margin_bottom(6)
            popbox.set_margin_start(6)
            popbox.set_margin_end(6)
        except Exception:
            pass
        popbox.append(cal)
        self._popover.set_child(popbox)
        try:
            self._cal_button.set_popover(self._popover)
        except Exception:
            pass

        # initial display update
        self._calendar = cal
        self._update_display()

        box.append(row)

        self._backend_widget = box
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        try:
            for w in (getattr(self, '_date_entry', None), getattr(self, '_cal_button', None), getattr(self, '_label_widget', None)):
                if w is not None:
                    w.set_sensitive(bool(enabled))
        except Exception:
            pass

    def _update_display(self):
        try:
            if getattr(self, '_date_entry', None) is not None:
                try:
                    fmt = self._get_locale_date_fmt()
                    d = getattr(self, '_date', None) or datetime.date(1, 1, 1)
                    txt = d.strftime(fmt)
                except Exception:
                    d = getattr(self, '_date', None)
                    if d is None:
                        txt = ''
                    else:
                        txt = d.isoformat()
                self._date_entry.set_text(txt)
        except Exception:
            pass

    def _set_date(self, newdate: datetime.date):
        '''
        copies newdate into internal value and updates gtk.entry display
        
        :param self: this instance
        :param newdate: new date value
        :type newdate: datetime.date
        '''
        try:
            self._date = newdate
            ## update entry display
            self._update_display()
        except Exception:
            pass
