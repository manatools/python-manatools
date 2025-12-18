# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains all Qt backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''
from PySide6 import QtWidgets
from ...yui_common import *

class YSelectionBoxQt(YSelectionWidget):
    def __init__(self, parent=None, label=""):
        super().__init__(parent)
        self._label = label
        self._value = ""
        self._selected_items = []
        self._multi_selection = False
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)
    
    def widgetClass(self):
        return "YSelectionBox"
    
    def value(self):
        return self._value
    
    def setValue(self, text):
        self._value = text
        if hasattr(self, '_list_widget') and self._list_widget:
            # Find and select the item with matching text
            for i in range(self._list_widget.count()):
                item = self._list_widget.item(i)
                if item.text() == text:
                    self._list_widget.setCurrentItem(item)
                    break
        # Update selected_items to keep internal state consistent
        self._selected_items = []
        for item in self._items:
            if item.label() == text:
                self._selected_items.append(item)
                break
    
    def label(self):
        return self._label
    
    def selectedItems(self):
        """Get list of selected items"""
        return self._selected_items
    
    def selectItem(self, item, selected=True):
        """Select or deselect a specific item"""
        if hasattr(self, '_list_widget') and self._list_widget:
            for i in range(self._list_widget.count()):
                list_item = self._list_widget.item(i)
                if list_item.text() == item.label():
                    if selected:
                        self._list_widget.setCurrentItem(list_item)
                        if item not in self._selected_items:
                            self._selected_items.append(item)
                    else:
                        if item in self._selected_items:
                            self._selected_items.remove(item)
                    break

    def setMultiSelection(self, enabled):
        """Enable or disable multi-selection."""
        self._multi_selection = bool(enabled)
        if hasattr(self, '_list_widget') and self._list_widget:
            mode = QtWidgets.QAbstractItemView.MultiSelection if self._multi_selection else QtWidgets.QAbstractItemView.SingleSelection
            self._list_widget.setSelectionMode(mode)
            # if disabling multi-selection, collapse to the first selected item
            if not self._multi_selection:
                selected = self._list_widget.selectedItems()
                if len(selected) > 1:
                    first = selected[0]
                    self._list_widget.clearSelection()
                    first.setSelected(True)
                    # update internal state to reflect change
                    self._on_selection_changed()

    def multiSelection(self):
        """Return whether multi-selection is enabled."""
        return bool(self._multi_selection)
    
    def _create_backend_widget(self):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if self._label:
            label = QtWidgets.QLabel(self._label)
            layout.addWidget(label)
        
        list_widget = QtWidgets.QListWidget()
        mode = QtWidgets.QAbstractItemView.MultiSelection if self._multi_selection else QtWidgets.QAbstractItemView.SingleSelection
        list_widget.setSelectionMode(mode)
        
        # Add items to list widget
        for item in self._items:
            list_widget.addItem(item.label())

        # Reflect model's selected flags into the view.
        # If multi-selection is enabled, select all items flagged selected.
        # If single-selection, only the last item with selected()==True should be selected.
        try:
            if self._multi_selection:
                for idx, item in enumerate(self._items):
                    try:
                        if item.selected():
                            li = list_widget.item(idx)
                            if li is not None:
                                li.setSelected(True)
                                if item not in self._selected_items:
                                    self._selected_items.append(item)
                                if not self._value:
                                    self._value = item.label()
                    except Exception:
                        pass
            else:
                last_selected_idx = None
                for idx, item in enumerate(self._items):
                    try:
                        if item.selected():
                            last_selected_idx = idx
                    except Exception:
                        pass
                if last_selected_idx is not None:
                    li = list_widget.item(last_selected_idx)
                    if li is not None:
                        list_widget.setCurrentItem(li)
                        li.setSelected(True)
                        # update model internal selection list and value
                        try:
                            self._selected_items = [self._items[last_selected_idx]]
                            self._value = self._items[last_selected_idx].label()
                        except Exception:
                            pass
        except Exception:
            pass

        list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(list_widget)
        
        self._backend_widget = container
        self._backend_widget.setEnabled(bool(self._enabled))
        self._list_widget = list_widget

    def _set_backend_enabled(self, enabled):
        """Enable/disable the selection box and its list widget; propagate where applicable."""
        try:
            if getattr(self, "_list_widget", None) is not None:
                try:
                    self._list_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass

    def addItem(self, item):
        """Add a single item to the selection box (model + Qt view)."""
        # Let base class normalize strings to YItem and append to _items
        super().addItem(item)

        # The newly added item is the last in the model list
        try:
            new_item = self._items[-1]
        except Exception:
            return

        # Ensure index is set
        try:
            new_item.setIndex(len(self._items) - 1)
        except Exception:
            pass

        # If the backend list widget exists, append a visual entry
        try:
            if getattr(self, '_list_widget', None) is not None:
                try:
                    self._list_widget.addItem(new_item.label())
                    # If the item is marked selected in the model, reflect it.
                    if new_item.selected():
                        idx = self._list_widget.count() - 1
                        list_item = self._list_widget.item(idx)
                        if list_item is not None:
                            # For single-selection, clear previous selections so
                            # only the newly-added selected item remains selected.
                            if not self._multi_selection:
                                try:
                                    self._list_widget.clearSelection()
                                except Exception:
                                    pass
                                # Also clear model-side selected flags for other items
                                for it in self._items[:-1]:
                                    try:
                                        it.setSelected(False)
                                    except Exception:
                                        pass
                                self._selected_items = []

                            list_item.setSelected(True)
                        if new_item not in self._selected_items:
                            self._selected_items.append(new_item)
                        # Update value to the newly selected item (single or last)
                        try:
                            self._value = new_item.label()
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

    def _on_selection_changed(self):
        """Handle selection change in the list widget"""
        if hasattr(self, '_list_widget') and self._list_widget:
            # Update selected items
            self._selected_items = []
            selected_indices = [index.row() for index in self._list_widget.selectedIndexes()]
            
            for idx in selected_indices:
                if idx < len(self._items):
                    self._selected_items.append(self._items[idx])
            
            # Update value to first selected item
            if self._selected_items:
                self._value = self._selected_items[0].label()
            
            # Post selection-changed event to containing dialog
            try:
                if self.notify():
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
            except Exception:
                pass

    def deleteAllItems(self):
        """Remove all items from the selection box, both in the model and the Qt view."""
        # Clear internal model state
        super().deleteAllItems()
        self._value = ""
        self._selected_items = []

        # Clear Qt list widget if present
        try:
            if getattr(self, '_list_widget', None) is not None:
                try:
                    self._list_widget.clear()
                except Exception:
                    pass
        except Exception:
            pass

