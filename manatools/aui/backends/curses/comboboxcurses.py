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
        self._height = 1
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
        # Update selected items
        self._selected_items = []
        for item in self._items:
            if item.label() == text:
                self._selected_items.append(item)
                break
    
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

    def _draw(self, window, y, x, width, height):
        # Store position and dimensions for dropdown drawing
        self._combo_y = y
        self._combo_x = x
        self._combo_width = width

        try:
            # Calculate available space for combo box
            label_space = len(self._label) + 1 if self._label else 0
            combo_space = width - label_space

            if combo_space <= 3:
                return

            # Draw label
            if self._label:
                label_text = self._label
                if len(label_text) > label_space - 1:
                    label_text = label_text[:label_space - 1]
                lbl_attr = curses.A_NORMAL
                if not self.isEnabled():
                    lbl_attr |= curses.A_DIM
                window.addstr(y, x, label_text, lbl_attr)
                x += len(label_text) + 1

            # Prepare display value
            display_value = self._value if self._value else "Select..."
            max_display_width = combo_space - 3
            if len(display_value) > max_display_width:
                display_value = display_value[:max_display_width] + "..."

            # Draw combo box background
            if not self.isEnabled():
                attr = curses.A_DIM
            else:
                attr = curses.A_REVERSE if self._focused else curses.A_NORMAL

            combo_bg = " " * combo_space
            window.addstr(y, x, combo_bg, attr)

            combo_text = f" {display_value} ▼"
            if len(combo_text) > combo_space:
                combo_text = combo_text[:combo_space]

            window.addstr(y, x, combo_text, attr)

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
           
            # Calculate dropdown position - right below the combo box
            dropdown_y = self._combo_y + 1
            dropdown_x = self._combo_x + (len(self._label) + 1 if self._label else 0)
            dropdown_width = self._combo_width - (len(self._label) + 1 if self._label else 0)
           
            # If not enough space below, draw above
            if dropdown_y + list_height >= screen_height:
                dropdown_y = max(1, self._combo_y - list_height - 1)
            
            # Ensure dropdown doesn't go beyond right edge
            if dropdown_x + dropdown_width >= screen_width:
                dropdown_width = screen_width - dropdown_x - 1
            
            if dropdown_width <= 5:  # Need reasonable width
                return
            
            # Draw dropdown background for each item
            for i in range(list_height):
                if i >= len(self._items):
                    break
                    
                item = self._items[i]
                item_text = item.label()
                if len(item_text) > dropdown_width - 2:
                    item_text = item_text[:dropdown_width - 2] + "..."
                
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
                        pass  # Ignore out-of-bounds errors
                
        except curses.error as e:
            try:
                self._logger.error("_draw_expanded_list curses.error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_draw_expanded_list curses.error: %s", e, exc_info=True)

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled():
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
