#!/usr/bin/env python3
# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.curses contains all curses backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.curses
'''
import curses
import curses.ascii
import sys
import os
import time
import logging
from ...yui_common import *

# Module-level logger for radiobutton curses backend
_mod_logger = logging.getLogger("manatools.aui.curses.radiobutton.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)


class YRadioButtonCurses(YWidget):
    def __init__(self, parent=None, label="", is_checked=False):
        super().__init__(parent)
        self._label = label
        self._is_checked = bool(is_checked)
        self._focused = False
        self._can_focus = True
        self._height = 1
        # per-instance logger
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        self._logger.debug("%s.__init__ label=%s checked=%s", self.__class__.__name__, label, is_checked)

    def widgetClass(self):
        return "YRadioButton"

    def value(self):
        return self._is_checked

    def setValue(self, checked):
        # Programmatic set: enforce single-selection among siblings when setting True
        try:
            self._is_checked = bool(checked)
            if self._is_checked:
                # uncheck sibling radio buttons under same parent
                try:
                    parent = getattr(self, '_parent', None)
                    if parent is not None:
                        for sib in list(getattr(parent, '_children', []) or []):
                            try:
                                if sib is not self and getattr(sib, 'widgetClass', None) and sib.widgetClass() == 'YRadioButton':
                                    if getattr(sib, '_is_checked', False):
                                        try:
                                            sib._is_checked = False
                                        except Exception:
                                            pass
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            pass

    def label(self):
        return self._label

    def _create_backend_widget(self):
        try:
            # associate placeholder backend widget
            self._backend_widget = self
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception as e:
            try:
                self._logger.error("_create_backend_widget error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_create_backend_widget error: %s", e, exc_info=True)

    def _set_backend_enabled(self, enabled):
        """Enable/disable radio button: update focusability and collapse focus if disabling."""
        try:
            if not hasattr(self, "_saved_can_focus"):
                self._saved_can_focus = getattr(self, "_can_focus", True)
            if not enabled:
                try:
                    self._saved_can_focus = self._can_focus
                except Exception:
                    self._saved_can_focus = True
                self._can_focus = False
                if getattr(self, "_focused", False):
                    self._focused = False
            else:
                try:
                    self._can_focus = bool(getattr(self, "_saved_can_focus", True))
                except Exception:
                    self._can_focus = True
        except Exception:
            pass

    def _draw(self, window, y, x, width, height):
        if self._visible is False:
            return
        try:
            # Use parentheses style for radio: '(*)' if checked else '( )'
            radio_symbol = "(*)" if self._is_checked else "( )"
            text = f"{radio_symbol} {self._label}"
            if len(text) > width:
                text = text[:max(0, width - 1)] + "…"

            attr_on = False
            if self._focused and self.isEnabled():
                window.attron(curses.A_REVERSE)
                attr_on = True
            elif not self.isEnabled():
                window.attron(curses.A_DIM)
                attr_on = True

            window.addstr(y, x, text)

            if attr_on:
                try:
                    if self._focused and self.isEnabled():
                        window.attroff(curses.A_REVERSE)
                    else:
                        window.attroff(curses.A_DIM)
                except Exception:
                    pass
        except curses.error as e:
            try:
                self._logger.error("_draw curses.error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_draw curses.error: %s", e, exc_info=True)

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled() or not self.visible():
            return False
        # Space or Enter to select radio
        if key in (ord(' '), ord('\n'), curses.KEY_ENTER):
            self._select()
            return True
        return False

    def _select(self):
        """Select this radio and unselect siblings; post event."""
        try:
            if not getattr(self, '_is_checked', False):
                # set self selected
                self._is_checked = True
                # uncheck siblings under same parent
                try:
                    parent = getattr(self, '_parent', None)
                    if parent is not None:
                        for sib in list(getattr(parent, '_children', []) or []):
                            try:
                                if sib is not self and getattr(sib, 'widgetClass', None) and sib.widgetClass() == 'YRadioButton':
                                    try:
                                        sib._is_checked = False
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                except Exception:
                    pass

                # Post notification event
                if self.notify():
                    dlg = self.findDialog()
                    if dlg is not None:
                        try:
                            dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
                        except Exception as e:
                            try:
                                self._logger.error("_select post event error: %s", e, exc_info=True)
                            except Exception:
                                _mod_logger.error("_select post event error: %s", e, exc_info=True)
                    else:
                        try:
                            print(f"RadioButton selected (no dialog): {self._label}")
                        except Exception:
                            pass
        except Exception:
            try:
                self._logger.error("_select error", exc_info=True)
            except Exception:
                _mod_logger.error("_select error", exc_info=True)

    def setVisible(self, visible=True):
        super().setVisible(visible)
        # in curses backend visibility controls whether widget can receive focus
        self._can_focus = bool(visible)