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
from ...yui_common import *
from .commoncurses import _curses_recursive_min_height

class YCheckBoxFrameCurses(YSingleChildContainerWidget):
    """
    NCurses implementation of a framed container with a checkbox in the title.
    The checkbox enables/disables the inner child (autoEnable/invertAutoEnable supported).
    Drawing reuses frame style from framecurses but prepends a checkbox marker to the title.
    """
    def __init__(self, parent=None, label: str = "", checked: bool = False):
        super().__init__(parent)
        self._label = label or ""
        self._checked = bool(checked)
        self._auto_enable = True
        self._invert_auto = False
        self._backend_widget = None
        # minimal height (will be computed from child)
        self._height = 3
        self._inner_top_padding = 1
        # allow focusing the frame title/checkbox and track focus state
        try:
            self._can_focus = True
        except Exception:
            pass
        self._focused = False

    def widgetClass(self):
        return "YCheckBoxFrame"

    def label(self):
        return self._label

    def setLabel(self, new_label):
        try:
            self._label = str(new_label)
        except Exception:
            self._label = new_label

    def value(self):
        try:
            return bool(self._checked)
        except Exception:
            return False

    def setValue(self, isChecked: bool):
        try:
            self._checked = bool(isChecked)
            # propagate enablement to children if autoEnable
            if self._auto_enable:
                self._apply_children_enablement(self._checked)
            # notify listeners
            try:
                if self.notify():
                    dlg = self.findDialog()
                    if dlg:
                        dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
            except Exception:
                pass
        except Exception:
            pass

    def autoEnable(self):
        return bool(self._auto_enable)

    def setAutoEnable(self, autoEnable: bool):
        try:
            self._auto_enable = bool(autoEnable)
            self._apply_children_enablement(self._checked)
        except Exception:
            pass

    def invertAutoEnable(self):
        return bool(self._invert_auto)

    def setInvertAutoEnable(self, invert: bool):
        try:
            self._invert_auto = bool(invert)
            self._apply_children_enablement(self._checked)
        except Exception:
            pass

    def stretchable(self, dim):
        """Frame is stretchable if its child is."""
        try:            
            child = self.child()
            if child is None:
                return False
            try:
                if bool(child.stretchable(dim)):
                    return True
            except Exception:
                pass
            try:
                if bool(child.weight(dim)):
                    return True
            except Exception:
                pass
        except Exception:
            pass
        return False

    def _update_min_height(self):
        """Recompute minimal height: borders + padding + child's minimal layout."""
        try:
            child = self.child()
            inner_min = _curses_recursive_min_height(child) if child is not None else 1
            self._height = max(3, 2 + self._inner_top_padding + inner_min)
        except Exception:
            self._height = max(self._height, 3)

    def _create_backend_widget(self):
        # no persistent backend object for curses
        self._backend_widget = None
        self._update_min_height()
        # ensure children enablement matches checkbox initial state
        try:
            self._apply_children_enablement(self._checked)
        except Exception:
            pass

    def _apply_children_enablement(self, isChecked: bool):
        try:
            if not self._auto_enable:
                return
            state = bool(isChecked)
            if self._invert_auto:
                state = not state
            child = self.child()
            if child is None:
                return
            try:
                child.setEnabled(state)
            except Exception:
                # best-effort try backend widget sensitivity
                try:
                    w = child.get_backend_widget()
                    if w is not None:
                        try:
                            w.set_sensitive(state)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

    def _set_backend_enabled(self, enabled: bool):
        try:
            # logical propagation
            # If auto_enable is enabled, child's enabled state follows checkbox.
            # Otherwise follow explicit enabled flag.
            if self._auto_enable:
                self._apply_children_enablement(self._checked)
            else:
                # propagate explicit enabled/disabled to logical children
                child = self.child()
                if child is not None:
                    child.setEnabled(enabled)
        except Exception:
            pass

    def addChild(self, child):
        super().addChild(child)        
        self._update_min_height()
        try:
            self._apply_children_enablement(self._checked)
        except Exception:
            pass

    def _on_toggle_request(self):
        """Toggle value (helper for key handling if needed)."""
        try:
            self.setValue(not self._checked)
        except Exception:
            pass

    def _handle_key(self, key):
        """Handle keyboard toggling when this frame is focused."""
        try:
            if key in (ord(' '), 10, 13, curses.KEY_ENTER):
                # toggle checkbox
                try:
                    self.setValue(not self._checked)
                except Exception:
                    pass
                return True
        except Exception:
            pass
        return False

    def _set_focus(self, focused: bool):
        """Called by container when focus moves; track focus for drawing."""
        try:
            self._focused = bool(focused)
        except Exception:
            self._focused = False

    def _draw(self, window, y, x, width, height):
        """
        Draw framed box with checkbox marker in the label, then delegate to child.
        Title shows "[x]" or "[ ]" before the label.
        """
        try:
            if width <= 0 or height <= 0:
                return
            self._update_min_height()
            # if not enough space for full frame, draw compact title line and return
            if height < 3 or width < 4:
                try:
                    chk = "x" if self._checked else " "
                    title = f"[{chk}] {self._label}" if self._label else f"[{chk}]"
                    title = title[:max(0, width)]
                    # highlight when focused, dim when disabled
                    attr = curses.A_BOLD
                    try:
                        if getattr(self, "isEnabled", None):
                            enabled = bool(self.isEnabled())
                        else:
                            enabled = True
                    except Exception:
                        enabled = True
                    if not enabled:
                        attr |= curses.A_DIM
                    if getattr(self, "_focused", False):
                        attr |= curses.A_REVERSE
                    window.addstr(y, x, title, attr)
                except curses.error:
                    pass
                return

            # choose box chars
            try:
                hline = curses.ACS_HLINE
                vline = curses.ACS_VLINE
                tl = curses.ACS_ULCORNER
                tr = curses.ACS_URCORNER
                bl = curses.ACS_LLCORNER
                br = curses.ACS_LRCORNER
            except Exception:
                hline = ord('-')
                vline = ord('|')
                tl = ord('+')
                tr = ord('+')
                bl = ord('+')
                br = ord('+')

            # draw border
            try:
                window.addch(y, x, tl)
                window.addch(y, x + width - 1, tr)
                window.addch(y + height - 1, x, bl)
                window.addch(y + height - 1, x + width - 1, br)
                for cx in range(x + 1, x + width - 1):
                    window.addch(y, cx, hline)
                    window.addch(y + height - 1, cx, hline)
                for cy in range(y + 1, y + height - 1):
                    window.addch(cy, x, vline)
                    window.addch(cy, x + width - 1, vline)
            except curses.error:
                pass

            # build title with checkbox marker
            try:
                chk = "x" if self._checked else " "
                title_body = f"[{chk}] {self._label}" if self._label else f"[{chk}]"
                max_title_len = max(0, width - 4)
                if len(title_body) > max_title_len:
                    title_body = title_body[:max(0, max_title_len - 3)] + "..."
                start_x = x + max(1, (width - len(title_body)) // 2)
                # choose attributes depending on focus/enable state
                attr = curses.A_BOLD
                try:
                    if getattr(self, "isEnabled", None):
                        enabled = bool(self.isEnabled())
                    else:
                        enabled = True
                except Exception:
                    enabled = True
                if not enabled:
                    attr |= curses.A_DIM
                if getattr(self, "_focused", False):
                    attr |= curses.A_REVERSE
                window.addstr(y, start_x, title_body, attr)
            except curses.error:
                pass

            # inner rect
            inner_x = x + 1
            inner_y = y + 1
            inner_w = max(0, width - 2)
            inner_h = max(0, height - 2)

            pad_top = min(self._inner_top_padding, max(0, inner_h))
            content_y = inner_y + pad_top
            content_h = max(0, inner_h - pad_top)

            child = getattr(self, "_child", None)
            if child is None:
                return

            needed = _curses_recursive_min_height(child)
            # ensure we give at least needed rows if available
            content_h = min(max(content_h, needed), inner_h)

            if content_h <= 0 or inner_w <= 0:
                return

            if hasattr(child, "_draw"):
                child._draw(window, content_y, inner_x, inner_w, content_h)
        except Exception:
            pass
