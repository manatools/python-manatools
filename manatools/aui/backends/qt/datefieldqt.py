# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains all qt backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''
from PySide6 import QtWidgets, QtCore
import logging
from ...yui_common import *


class YDateFieldQt(YWidget):
    """Qt backend YDateField implementation using QDateEdit.
    value()/setValue() use ISO format YYYY-MM-DD. No change events posted.
    """
    def __init__(self, parent=None, label: str = ""):
        super().__init__(parent)
        self._label = label or ""
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        self._date = QtCore.QDate.currentDate()

    def widgetClass(self):
        return "YDateField"

    def value(self) -> str:
        try:
            return self._date.toString("yyyy-MM-dd")
        except Exception:
            return ""

    def setValue(self, datestr: str):
        try:
            parts = str(datestr).split("-")
            if len(parts) == 3:
                y, m, d = [int(p) for p in parts]
                qd = QtCore.QDate(y, m, d)
                if qd.isValid():
                    self._date = qd
                    if getattr(self, '_dateedit', None) is not None:
                        try:
                            self._dateedit.setDate(self._date)
                        except Exception:
                            pass
        except Exception:
            try:
                self._logger.debug("Invalid date for setValue: %r", datestr)
            except Exception:
                pass

    def _on_date_changed(self, qdate):
        """Update internal date when the QDateEdit value changes in the UI."""
        try:
            # qdate is a QtCore.QDate
            self._date = qdate
        except Exception:
            try:
                self._logger.debug("_on_date_changed: couldn't set date from %r", qdate)
            except Exception:
                pass

    def _create_backend_widget(self):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        if self._label:
            lbl = QtWidgets.QLabel(self._label)
            layout.addWidget(lbl)
            self._label_widget = lbl

        de = QtWidgets.QDateEdit()
        try:
            de.setCalendarPopup(True)
        except Exception:
            pass
        try:
            # Display in system locale for user friendliness
            loc = QtCore.QLocale.system()
            fmt = loc.dateFormat(QtCore.QLocale.FormatType.ShortFormat)
            if fmt:
                de.setDisplayFormat(fmt)
        except Exception:
            pass
        try:
            de.setDate(self._date)
        except Exception:
            pass
        try:
            # keep internal date in sync when user selects a new date
            de.dateChanged.connect(self._on_date_changed)
        except Exception:
            try:
                self._logger.debug("could not connect dateChanged signal")
            except Exception:
                pass
        # Do not emit any events; value is read on demand
        layout.addWidget(de)
        self._backend_widget = container
        self._dateedit = de
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

        # Apply size policy from stretchable hints
        try:
            sp = container.sizePolicy()
            try:
                horiz = QtWidgets.QSizePolicy.Policy.Expanding if self.stretchable(YUIDimension.YD_HORIZ) else QtWidgets.QSizePolicy.Policy.Preferred
                vert = QtWidgets.QSizePolicy.Policy.Expanding if self.stretchable(YUIDimension.YD_VERT) else QtWidgets.QSizePolicy.Policy.Fixed
            except Exception:
                horiz = QtWidgets.QSizePolicy.Expanding if self.stretchable(YUIDimension.YD_HORIZ) else QtWidgets.QSizePolicy.Preferred
                vert = QtWidgets.QSizePolicy.Expanding if self.stretchable(YUIDimension.YD_VERT) else QtWidgets.QSizePolicy.Fixed
            sp.setHorizontalPolicy(horiz)
            sp.setVerticalPolicy(vert)
            container.setSizePolicy(sp)
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        try:
            if getattr(self, '_dateedit', None) is not None:
                self._dateedit.setEnabled(bool(enabled))
        except Exception:
            pass
        try:
            if getattr(self, '_label_widget', None) is not None:
                self._label_widget.setEnabled(bool(enabled))
        except Exception:
            pass
