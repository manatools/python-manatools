# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains all Qt backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''
from PySide6 import QtWidgets, QtGui
import logging
from ...yui_common import *
from .commonqt import _resolve_icon

class YTreeQt(YSelectionWidget):
    """
    Qt backend for YTree (based on YTree.h semantics).
    - Supports multiSelection and immediateMode.
    - Rebuild tree from internal items with rebuildTree().
    - currentItem() returns the YTreeItem wrapper for the focused/selected QTreeWidgetItem.
    - activate() simulates user activation of the current item (posts an Activated event).
    - recursiveSelection if it should select children recursively
    """
    def __init__(self, parent=None, label="", multiSelection=False, recursiveSelection=False):
        super().__init__(parent)
        self._label = label
        self._multi = bool(multiSelection)
        self._recursive = bool(recursiveSelection)
        if self._recursive:
            self._multi = True  # recursive selection implies multi-selection
        self._immediate = self.notify()
        self._backend_widget = None
        self._tree_widget = None
        # mappings between QTreeWidgetItem and logical YTreeItem (python objects in self._items)
        self._qitem_to_item = {}
        self._item_to_qitem = {}
        # guard to avoid recursion when programmatically changing selection
        self._suppress_selection_handler = False
        # remember last selected QTreeWidgetItem set to detect added/removed selections
        self._last_selected_qitems = set()
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")            

    def widgetClass(self):
        return "YTree"

    def _create_backend_widget(self):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if self._label:
            lbl = QtWidgets.QLabel(self._label)
            layout.addWidget(lbl)

        tree = QtWidgets.QTreeWidget()
        tree.setHeaderHidden(True)
        mode = QtWidgets.QAbstractItemView.MultiSelection if self._multi else QtWidgets.QAbstractItemView.SingleSelection
        tree.setSelectionMode(mode)
        tree.itemSelectionChanged.connect(self._on_selection_changed)
        tree.itemActivated.connect(self._on_item_activated)

        layout.addWidget(tree)
        self._backend_widget = container
        self._tree_widget = tree
        self._backend_widget.setEnabled(bool(self._enabled))
        # populate if items already present
        try:
            self.rebuildTree()
        except Exception:            
            self._logger.error("rebuildTree failed during _create_backend_widget", exc_info=True)


    def rebuildTree(self):
        """Rebuild the QTreeWidget from self._items (calls helper recursively)."""
        self._logger.debug("rebuildTree: rebuilding tree with %d items", len(self._items) if self._items else 0)
        if self._tree_widget is None:
            # ensure backend exists
            self._create_backend_widget()
        # clear existing
        self._qitem_to_item.clear()
        self._item_to_qitem.clear()
        self._tree_widget.clear()
        # collect selected candidates while building so we can apply single-selection rules
        selected_candidates = []

        def _add_recursive(parent_qitem, item):
            # item expected to provide label() and possibly children() iterable
            text = ""
            try:
                text = item.label()
            except Exception:
                try:
                    text = str(item)
                except Exception:
                    text = ""
            qitem = QtWidgets.QTreeWidgetItem([text])
            # preserve mapping
            self._qitem_to_item[qitem] = item
            self._item_to_qitem[item] = qitem
            # set icon for this item if provided
            try:
                icon_name = None
                fn = getattr(item, 'iconName', None)
                if callable(fn):
                    icon_name = fn()
                else:
                    icon_name = fn
                if icon_name:
                    ico = _resolve_icon(icon_name)
                    if ico is not None:
                        try:
                            self._logger.debug("Column count for item %d", qitem.columnCount())
                            qitem.setIcon(0, ico)
                        except Exception:
                            pass
            except Exception:
                self._logger.error("Error setting icon for tree item %s", text, exc_info=True)
                pass
            # attach to parent or top-level
            if parent_qitem is None:
                self._tree_widget.addTopLevelItem(qitem)
            else:
                parent_qitem.addChild(qitem)

            # set expanded state according to the logical item's _is_open flag
            try:
                is_open = bool(getattr(item, "_is_open", False))
                # setExpanded ensures the node shows as expanded/collapsed
                qitem.setExpanded(is_open)
            except Exception:
                pass

            # remember selection candidates
            try:
                if getattr(item, 'selected', None) and callable(getattr(item, 'selected')):
                    if item.selected():
                        selected_candidates.append((qitem, item))
            except Exception:
                pass

            # recurse on children if available
            try:
                children = getattr(item, "children", None)
                if callable(children):
                    childs = children()
                else:
                    childs = children or []
            except Exception:
                childs = []
            # many YTreeItem implementations may expose _children or similar; try common patterns
            if not childs:
                try:
                    childs = getattr(item, "_children", []) or []
                except Exception:
                    childs = []

            for c in childs:
                _add_recursive(qitem, c)

            return qitem

        for it in list(getattr(self, "_items", []) or []):
            try:
                _add_recursive(None, it)
            except Exception:
                pass
        # Apply selection state according to collected candidates and selection mode
        try:
            self._selected_items = []
            if self._multi:
                for qit, it in selected_candidates:
                    try:
                        qit.setSelected(True)
                        if it not in self._selected_items:
                            self._selected_items.append(it)
                        try:
                            it.setSelected(True)
                        except Exception:
                            pass
                    except Exception:
                        pass
            else:
                if selected_candidates:
                    qit, it = selected_candidates[-1]
                    try:
                        qit.setSelected(True)
                        it.setSelected(True)
                        self._selected_items = [it]
                    except Exception:
                        pass
        except Exception:
            pass

        # do not call expandAll(); expansion is controlled per-item by _is_open

    def currentItem(self):
        """Return the logical YTreeItem corresponding to the current/focused QTreeWidgetItem."""
        if not self._tree_widget:
            return None
        try:
            qcur = self._tree_widget.currentItem()
            if qcur is None:
                # fallback to first selected item if current not set
                sel = self._tree_widget.selectedItems()
                qcur = sel[0] if sel else None
            if qcur is None:
                return None
            return self._qitem_to_item.get(qcur, None)
        except Exception:
            return None

    def activate(self):
        """Simulate activation of the current item (post Activated event)."""
        item = self.currentItem()
        if item is None:
            return False
        try:
            dlg = self.findDialog()
            if dlg is not None and self.notify():
                dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
            return True
        except Exception:
            return False

    def hasMultiSelection(self):
        """Return True if the tree allows selecting multiple items at once."""
        return bool(self._multi)

    def immediateMode(self):
        return bool(self._immediate)

    def setImmediateMode(self, on:bool=True):
        self._immediate = on
        self.setNotify(on)

    def _collect_descendant_qitems(self, qitem):
        """Return a list of qitem and all descendant QTreeWidgetItem objects."""
        out = []
        if qitem is None:
            return out
        stack = [qitem]
        while stack:
            cur = stack.pop()
            out.append(cur)
            try:
                for i in range(cur.childCount()):
                    stack.append(cur.child(i))
            except Exception:
                pass
        return out

    # selection change handler
    def _on_selection_changed(self):
        """Update logical selection list and emit selection-changed event when needed."""
        # Defensive guard: when we change selection programmatically we don't want to re-enter here.
        if self._suppress_selection_handler:
            return

        try:
            if not self._tree_widget:
                return

            sel_qitems = list(self._tree_widget.selectedItems())
            current_set = set(sel_qitems)

            # If recursive selection is enabled and multi-selection is allowed,
            # adjust selection so that selecting a parent selects all descendants
            # and deselecting a parent deselects all descendants.
            if self._recursive and self._multi:
                added = current_set - self._last_selected_qitems
                removed = self._last_selected_qitems - current_set

                # start desired_set from current_set
                desired_set = set(current_set)

                # For every newly added item, ensure its descendants are selected
                for q in list(added):
                    for dq in self._collect_descendant_qitems(q):
                        desired_set.add(dq)

                # For every removed item, ensure its descendants are deselected
                for q in list(removed):
                    for dq in self._collect_descendant_qitems(q):
                        if dq in desired_set:
                            desired_set.discard(dq)

                # If desired_set differs from what's currently selected in the widget,
                # apply the change programmatically.
                if desired_set != current_set:
                    try:
                        self._suppress_selection_handler = True
                        self._tree_widget.clearSelection()
                        for q in desired_set:
                            try:
                                q.setSelected(True)
                            except Exception:
                                pass
                    finally:
                        self._suppress_selection_handler = False
                    # refresh sel_qitems and current_set after modification
                    sel_qitems = list(self._tree_widget.selectedItems())
                    current_set = set(sel_qitems)

            # Build logical_qitems: if recursive + single select, include descendants in logical list;
            # otherwise logical_qitems mirrors current UI selection.
            logical_qitems = []
            if self._recursive and not self._multi:
                for q in sel_qitems:
                    logical_qitems.append(q)
                    for dq in self._collect_descendant_qitems(q):
                        if dq is not q:
                            logical_qitems.append(dq)
            else:
                logical_qitems = sel_qitems

            # Map qitems -> logical YTreeItem objects
            new_selected = []
            for qitem in logical_qitems:
                itm = self._qitem_to_item.get(qitem, None)
                if itm is not None:
                    new_selected.append(itm)

            # Update internal selected items list (logical selection used by base class)
            try:
                # clear previous selection flags for all known items
                for it in list(getattr(self, "_items", []) or []):
                    try:
                        it.setSelected(False)
                    except Exception:
                        pass
                # set selection flag for newly selected items
                for it in new_selected:
                    try:
                        it.setSelected(True)
                    except Exception:
                        pass
            except Exception:
                pass

            self._selected_items = new_selected

            # remember last selected QTreeWidgetItem set for next invocation
            try:
                self._last_selected_qitems = set(self._tree_widget.selectedItems())
            except Exception:
                self._last_selected_qitems = set()

            # immediate mode: notify container/dialog
            try:
                if self._immediate and self.notify():
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
            except Exception:
                pass
        except Exception:
            pass

    # item activated (double click / Enter)
    def _on_item_activated(self, qitem, column):
        try:
            # map to logical item
            item = self._qitem_to_item.get(qitem, None)
            if item is None:
                return
            # post activated event
            dlg = self.findDialog()
            if dlg is not None and self.notify():
                dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
        except Exception:
            pass

    def addItem(self, item):
        '''Add a YItem redefinition from YSelectionWidget to manage YTreeItems.'''
        if isinstance(item, str):
            item = YTreeItem(item)            
            super().addItem(item)
        elif isinstance(item, YTreeItem):
            super().addItem(item)
        else:
            self._logger.error("YTree.addItem: invalid item type %s", type(item))
            raise TypeError("YTree.addItem expects a YTreeItem or string label")
        # ensure index set
        try:
            item.setIndex(len(self._items) - 1)
        except Exception:
            pass
        # if backend exists, refresh tree to reflect new item (including icon/selection)
        try:
            if getattr(self, '_tree_widget', None) is not None:
                try:
                    self.rebuildTree()
                except Exception:
                    pass
        except Exception:
            pass

    # property API hooks (minimal implementation)
    def setProperty(self, propertyName, val):
        try:
            if propertyName == "immediateMode":
                self.setImmediateMode(bool(val))
                return True
        except Exception:
            pass
        return False

    def getProperty(self, propertyName):
        try:
            if propertyName == "immediateMode":
                return self.immediateMode()
        except Exception:
            pass
        return None

    def _set_backend_enabled(self, enabled):
        """Enable/disable the tree widget and propagate to logical items/widgets."""
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass
        # logical propagation to child YWidgets (if any)
        try:
            for c in list(getattr(self, "_items", []) or []):
                try:
                    if hasattr(c, "setEnabled"):
                        c.setEnabled(enabled)
                except Exception:
                    pass
        except Exception:
            pass

    def selectItem(self, item, selected=True):
        """Select or deselect the given logical YTreeItem and reflect in the view."""
        try:
            # update model flag
            try:
                item.setSelected(bool(selected))
            except Exception:
                pass
            # if no tree widget, only model is updated
            if getattr(self, '_tree_widget', None) is None:
                # maintain internal selected list
                if selected:
                    if item not in self._selected_items:
                        if not self._multi:
                            self._selected_items = [item]
                        else:
                            self._selected_items.append(item)
                else:
                    try:
                        if item in self._selected_items:
                            self._selected_items.remove(item)
                    except Exception:
                        pass
                return

            qit = self._item_to_qitem.get(item, None)
            if qit is None:
                # item may be newly added — rebuild tree and retry
                try:
                    self.rebuildTree()
                    qit = self._item_to_qitem.get(item, None)
                except Exception:
                    qit = None

            if qit is None:
                return

            # apply selection in view
            try:
                if not self._multi and selected:
                    try:
                        self._tree_widget.clearSelection()
                    except Exception:
                        pass
                # if recursive selection is enabled, select/deselect descendants too
                targets = [qit]
                if selected and self._recursive:
                    targets = self._collect_descendant_qitems(qit)
                for tq in targets:
                    try:
                        tq.setSelected(bool(selected))
                    except Exception:
                        pass
            except Exception:
                pass

            # update internal selected items list
            try:
                new_selected = []
                for q in self._tree_widget.selectedItems():
                    itm = self._qitem_to_item.get(q, None)
                    if itm is not None:
                        new_selected.append(itm)
                # if not multi, keep only last
                if not self._multi and len(new_selected) > 1:
                    new_selected = [new_selected[-1]]
                self._selected_items = new_selected
            except Exception:
                pass
        except Exception:
            pass

    def deleteAllItems(self):
        """Remove all items from model and QTreeWidget view."""
        try:
            super().deleteAllItems()
        except Exception:
            self._items = []
            self._selected_items = []
        try:
            self._qitem_to_item.clear()
        except Exception:
            pass
        try:
            self._item_to_qitem.clear()
        except Exception:
            pass
        try:
            if getattr(self, '_tree_widget', None) is not None:
                try:
                    self._tree_widget.clear()
                except Exception:
                    pass
        except Exception:
            pass
