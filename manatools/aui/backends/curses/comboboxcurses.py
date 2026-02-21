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

# Module-level logger for combobox curses backend
_mod_logger = logging.getLogger("manatools.aui.curses.combobox.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)


class YComboBoxCurses(YSelectionWidget):
    def __init__(self, parent=None, label="", editable=False):
        super().__init__(parent)
        self._label = label
        self._editable = editable
        self._value = ""
        self._focused = False
        self._can_focus = True
        # Reserve two lines: one for the label (caption) and one for the control
        self._height = 2 if self._label else 1
        self._expanded = False
        self._hover_index = 0
        self._combo_x = 0
        self._combo_y = 0
        self._combo_width = 0
        # per-instance logger
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        self._logger.debug("%s.__init__ label=%s editable=%s", self.__class__.__name__, label, editable)
    
    def widgetClass(self):
        return "YComboBox"
    
    def value(self):
        return self._value
    
    def setValue(self, text):
        self._value = text
        # Update selected items and ensure only one item selected
        try:
            self._selected_items = []
            for it in self._items:
                try:
                    sel = (it.label() == text)
                    it.setSelected(sel)
                    if sel:
                        self._selected_items.append(it)
                except Exception:
                    pass
        except Exception:
            self._selected_items = []

    def editable(self):
        return self._editable
    
    def _create_backend_widget(self):
        try:
            # associate a placeholder backend widget to avoid None
            self._backend_widget = self
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception as e:
            try:
                self._logger.error("_create_backend_widget error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_create_backend_widget error: %s", e, exc_info=True)

    def _set_backend_enabled(self, enabled):
        """Enable/disable combobox: affect focusability, expanded state and focused state."""
        try:
            if not hasattr(self, "_saved_can_focus"):
                self._saved_can_focus = getattr(self, "_can_focus", True)
            if not enabled:
                try:
                    self._saved_can_focus = self._can_focus
                except Exception:
                    self._saved_can_focus = True
                self._can_focus = False
                # collapse expanded dropdown if any
                try:
                    if getattr(self, "_expanded", False):
                        self._expanded = False
                except Exception:
                    pass
                if getattr(self, "_focused", False):
                    self._focused = False
            else:
                try:
                    self._can_focus = bool(getattr(self, "_saved_can_focus", True))
                except Exception:
                    self._can_focus = True
        except Exception:
            pass

    def setLabel(self, new_label):
        super().setLabel(new_label)
        self._height = 2 if self._label else 1
    
    def _draw(self, window, y, x, width, height):
        if self._visible is False:
            return
        # Store position and dimensions for dropdown drawing
        # Label is drawn on row `y`, combo control on row `y+1`.
        self._combo_y = y + 1 if self._label else y
        self._combo_x = x
        self._combo_width = width

        # require at least two rows (label + control)
        if height < self._height:
            return

        try:
            # Calculate available space for combo box (full width, label is above)
            combo_space = width
            if combo_space <= 3:
                return

            # Draw label on top row
            if self._label:
                label_text = self._label
                # clip label if too long for width
                if len(label_text) > width:
                    label_text = label_text[:max(0, width - 1)] + "…"
                lbl_attr = curses.A_NORMAL
                if not self.isEnabled():
                    lbl_attr |= curses.A_DIM
                try:
                    window.addstr(y, x, label_text, lbl_attr)
                except curses.error:
                    pass

            # Prepare display value and draw combo on next row
            display_value = self._value if self._value else "Select…"
            max_display_width = combo_space - 4  # account for " ▼" and padding
            if len(display_value) -1 > max_display_width:
                display_value = display_value[:max_display_width] + "…" 

            # Draw combo box background on the control row
            if not self.isEnabled():
                attr = curses.A_DIM
            else:
                attr = curses.A_REVERSE if self._focused else curses.A_NORMAL

            try:
                combo_bg = " " * combo_space
                window.addstr(self._combo_y, x, combo_bg, attr)
                combo_text = f" {display_value} ▼"
                if len(combo_text) > combo_space:
                    combo_text = combo_text[:combo_space]
                window.addstr(self._combo_y, x, combo_text, attr)
            except curses.error:
                pass

            # Draw expanded list if active and enabled
            if self._expanded and self.isEnabled():
                self._draw_expanded_list(window)
        except curses.error as e:
            try:
                self._logger.error("_draw curses.error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_draw curses.error: %s", e, exc_info=True)

    def _draw_expanded_list(self, window):
        """Draw the expanded dropdown list at correct position"""
        if not self._expanded or not self._items:
            return

        try:
            # Make sure we don't draw outside screen
            screen_height, screen_width = window.getmaxyx()

            list_height = min(len(self._items), screen_height)

            # Calculate dropdown position - right below the combo control row
            dropdown_y = self._combo_y + 1
            dropdown_x = self._combo_x
            try:
                # longest item label
                max_label_len = max((len(i.label()) for i in self._items), default=0)
            except Exception:
                max_label_len = 0
            # desired width includes small padding
            desired_width = max_label_len + 2
            # never exceed screen usable width (leave 1 column margin)
            max_allowed = max(5, screen_width - 2)
            dropdown_width = min(desired_width, max_allowed)
            # if popup would overflow to the right, shift it left so full text is visible when possible
            if dropdown_x + dropdown_width >= screen_width:
                shift = (dropdown_x + dropdown_width) - (screen_width - 1)
                dropdown_x = max(0, dropdown_x - shift)
            # ensure reasonable minimum
            if dropdown_width < 5:
                dropdown_width = 5

            if dropdown_y + list_height >= screen_height:
                dropdown_y = max(1, self._combo_y - list_height - 1)

            # Ensure dropdown doesn't go beyond right edge
            if dropdown_x + dropdown_width >= screen_width:
                dropdown_width = screen_width - dropdown_x - 1

            # Draw dropdown background for each item
            for i in range(list_height):
                if i >= len(self._items):
                    break

                item = self._items[i]
                item_text = item.label()
                if len(item_text) > dropdown_width - 2:
                    item_text = item_text[:dropdown_width - 2] + "…"

                # Highlight hovered item
                attr = curses.A_REVERSE if i == self._hover_index else curses.A_NORMAL

                # Create background for the item
                bg_text = " " + item_text.ljust(dropdown_width - 2)
                if len(bg_text) > dropdown_width:
                    bg_text = bg_text[:dropdown_width]

                # Ensure we don't write beyond screen bounds
                if (dropdown_y + i < screen_height and
                    dropdown_x < screen_width and
                    dropdown_x + len(bg_text) <= screen_width):
                    try:
                        window.addstr(dropdown_y + i, dropdown_x, bg_text, attr)
                    except curses.error:
                        pass

        except curses.error as e:
            try:
                self._logger.error("_draw_expanded_list curses.error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_draw_expanded_list curses.error: %s", e, exc_info=True)

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled() or not self.visible():
            return False           
        handled = True
        
        # If currently expanded, give expanded-list handling priority so Enter
        # selects the hovered item instead of simply toggling expansion.
        if self._expanded:
            # Handle navigation in expanded list
            if key == curses.KEY_UP:
                if self._hover_index > 0:
                    self._hover_index -= 1
            elif key == curses.KEY_DOWN:
                if self._hover_index < len(self._items) - 1:
                    self._hover_index += 1
            elif key == ord('\n') or key == ord(' '):
                # Select hovered item
                if self._items and 0 <= self._hover_index < len(self._items):
                    selected_item = self._items[self._hover_index]
                    self.setValue(selected_item.label())  # update internal value/selection
                    self._expanded = False
                    if self.notify():
                        # force parent dialog redraw if present
                        dlg = self.findDialog()
                        if dlg is not None:
                            try:
                                # notify dialog to redraw immediately
                                dlg._last_draw_time = 0
                                # post a widget event for selection change
                                dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
                            except Exception:
                                pass
                    # selection made -> handled
            elif key == 27:  # ESC key
                self._expanded = False
            else:
                handled = False
        else:
            # Not expanded: Enter/Space expands the list
            if key == ord('\n') or key == ord(' '):
                self._expanded = not self._expanded
                if self._expanded and self._items:
                    # Set hover index to current value if exists
                    self._hover_index = 0
                    if self._value:
                        for i, item in enumerate(self._items):
                            if item.label() == self._value:
                                self._hover_index = i
                                break
            else:
                handled = False
        
        return handled

    # New: addItem at runtime
    def addItem(self, item):
        try:
            super().addItem(item)
        except Exception:
            try:
                if isinstance(item, str):
                    super().addItem(item)
                else:
                    self._items.append(item)
            except Exception:
                return
        try:
            new_item = self._items[-1]
            new_item.setIndex(len(self._items) - 1)
        except Exception:
            pass

        # enforce single-selection semantics
        try:
            if new_item.selected():
                for it in self._items[:-1]:
                    try:
                        it.setSelected(False)
                    except Exception:
                        pass
                self._value = new_item.label()
                self._selected_items = [new_item]
        except Exception:
            pass

    def deleteAllItems(self):
        super().deleteAllItems()     
        self._value = ""
        self._expanded = False
        self._hover_index = 0

    def setVisible(self, visible=True):
        super().setVisible(visible)
        self._can_focus = visible