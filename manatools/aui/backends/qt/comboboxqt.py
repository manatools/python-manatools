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
from .commonqt import _resolve_icon as _qt_resolve_icon

class YComboBoxQt(YSelectionWidget):
    def __init__(self, parent=None, label="", editable=False):
        super().__init__(parent)
        self._label = label
        self._editable = editable
        self._value = ""
        self._selected_items = []
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        self._combo_widget = None
        # reference to the visual label widget (if any)
        self._label_widget = None
    
    def widgetClass(self):
        return "YComboBox"
    
    def value(self):
        return self._value
    
    def setValue(self, text):
        self._value = text
        if hasattr(self, '_combo_widget') and self._combo_widget:
            index = self._combo_widget.findText(text)
            if index >= 0:
                self._combo_widget.setCurrentIndex(index)
            elif self._editable:
                self._combo_widget.setEditText(text)
        # update selected_items to keep internal state consistent
        self._selected_items = []
        for item in self._items:
            if item.label() == text:
                self._selected_items.append(item)
                break
        try:
            # ensure selected flags consistent: only one selected
            for it in self._items:
                try:
                    it.setSelected(it.label() == text)
                except Exception:
                    pass
        except Exception:
            pass

    def editable(self):
        return self._editable
    
    def setLabel(self, new_label: str):
        """Set logical label and update/create the visual QLabel in the container."""
        try:
            super().setLabel(new_label)
            if self._label_widget is not None:
                self._label_widget.setText(new_label)
            else:
                # create and insert label before combo in layout
                if getattr(self, "_backend_widget", None) is not None and getattr(self, "_combo_widget", None) is not None:
                    try:
                        layout = self._backend_widget.layout()
                        if layout is not None:
                            label = QtWidgets.QLabel(new_label)
                            layout.insertWidget(0, label)
                            self._label_widget = label
                    except Exception:
                        self._logger.exception("setLabel: failed to insert new QLabel")
        except Exception:
            self._logger.exception("setLabel: error updating label=%r", new_label)

    def _create_backend_widget(self):
        container = QtWidgets.QWidget()
        # use vertical layout so label sits above the combo control
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if self._label:
            label = QtWidgets.QLabel(self._label)
            self._label_widget = label
            layout.addWidget(label)
        
        if self._editable:
            combo = QtWidgets.QComboBox()
            combo.setEditable(True)
        else:
            combo = QtWidgets.QComboBox()
        
        # Add items to combo box
        for item in self._items:
            try:
                icon_name = None
                try:
                    fn = getattr(item, 'iconName', None)
                    icon_name = fn() if callable(fn) else fn
                except Exception:
                    icon_name = None
                qicon = None
                if icon_name:
                    try:
                        qicon = _qt_resolve_icon(icon_name)
                    except Exception:
                        qicon = None
                if qicon is not None:
                    combo.addItem(qicon, item.label())
                else:
                    combo.addItem(item.label())
            except Exception:
                try:
                    combo.addItem(item.label())
                except Exception:
                    pass

        
        combo.currentTextChanged.connect(self._on_text_changed)
        # also handle index change (safer for some input methods)
        combo.currentIndexChanged.connect(lambda idx: self._on_text_changed(combo.currentText()))

        # pick initial selection: first item marked selected
        try:
            selected_idx = -1
            for idx, it in enumerate(self._items):
                try:
                    if it.selected():
                        selected_idx = idx
                        break
                except Exception:
                    pass
            if selected_idx >= 0:
                combo.setCurrentIndex(selected_idx)
                self._value = self._items[selected_idx].label()
                self._selected_items = [self._items[selected_idx]]
            else:
                self._selected_items = []
        except Exception:
            pass
        # Honor logical stretch/weight: set QSizePolicy and add with layout stretch factor
        try:
            try:
                weight_v = int(self.weight(YUIDimension.YD_VERT))
            except Exception:
                weight_v = 0
            try:
                stretchable_v = bool(self.stretchable(YUIDimension.YD_VERT))
            except Exception:
                stretchable_v = False
            stretch = weight_v if weight_v > 0 else (1 if stretchable_v else 0)

            # set QSizePolicy according to logical flags
            try:
                sp = combo.sizePolicy()
                try:
                    horiz = QtWidgets.QSizePolicy.Expanding if bool(self.stretchable(YUIDimension.YD_HORIZ)) else QtWidgets.QSizePolicy.Fixed
                except Exception:
                    horiz = QtWidgets.QSizePolicy.Fixed
                try:
                    vert = QtWidgets.QSizePolicy.Expanding if stretch > 0 else QtWidgets.QSizePolicy.Fixed
                except Exception:
                    vert = QtWidgets.QSizePolicy.Fixed
                sp.setHorizontalPolicy(horiz)
                sp.setVerticalPolicy(vert)
                combo.setSizePolicy(sp)
            except Exception:
                pass

            # add to layout with stretch factor when supported (vertical layout: label above, combo below)
            added = False
            try:
                layout.addWidget(combo, stretch)
                added = True
            except TypeError:
                added = False
            except Exception:
                added = False

            if not added:
                try:
                    layout.addWidget(combo)
                except Exception:
                    try:
                        combo.setParent(container)
                    except Exception:
                        pass
        except Exception:
            try:
                layout.addWidget(combo)
            except Exception:
                pass
         
        self._backend_widget = container
        self._combo_widget = combo
        self._backend_widget.setEnabled(bool(self._enabled))
        # allow logger to raise if misconfigured
        self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())

    def _set_backend_enabled(self, enabled):
        """Enable/disable the combobox and its container."""
        try:
            if getattr(self, "_combo_widget", None) is not None:
                try:
                    self._combo_widget.setEnabled(bool(enabled))
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

    # New: add single item at runtime
    def addItem(self, item):
        super().addItem(item)
        new_item = self._items[-1]
        
        # update backend widget if present
        if getattr(self, "_combo_widget", None):
            try:
                icon_name = None
                try:
                    fn = getattr(new_item, 'iconName', None)
                    icon_name = fn() if callable(fn) else fn
                except Exception:
                    icon_name = None
                qicon = None
                if icon_name:
                    try:
                        qicon = _qt_resolve_icon(icon_name)
                    except Exception:
                        qicon = None
                if qicon is not None:
                    self._combo_widget.addItem(qicon, new_item.label())
                else:
                    self._combo_widget.addItem(new_item.label())
                # reflect selection state
                try:
                    if new_item.selected():
                        # ensure only one is selected
                        for it in self._items:
                            try:
                                it.setSelected(False)
                            except Exception:
                                pass
                        new_item.setSelected(True)
                        idx = len(self._items) - 1
                        self._combo_widget.setCurrentIndex(idx)
                        self._selected_items = [new_item]
                        self._value = new_item.label()
                except Exception:
                    pass
            except Exception:
                pass

    # New: delete all items at runtime
    def deleteAllItems(self):
        try:
            self._items = []
            self._selected_items = []
            self._value = ""
        except Exception:
            pass
        if getattr(self, "_combo_widget", None):
            try:
                self._combo_widget.clear()
            except Exception:
                # fallback: recreate widget if clear not supported
                try:
                    parent = self._combo_widget.parent()
                    layout = self._combo_widget.parent().layout() if parent is not None else None
                    if layout is not None:
                        try:
                            layout.removeWidget(self._combo_widget)
                            self._combo_widget.deleteLater()
                        except Exception:
                            pass
                except Exception:
                    pass

    def _on_text_changed(self, text):
        # keep previous behaviour, but update model selection flags robustly
        try:
            self._value = text
        except Exception:
            self._value = text
        # update selected items: only one selected in combo
        try:
            old_item = self._selected_items[0] if self._selected_items else None
            if old_item:
                old_item.setSelected( False )
            self._selected_items = []
            for it in self._items:
                try:
                    was = (it.label() == text)
                    it.setSelected(was)
                    if was:
                        self._selected_items.append(it)
                except Exception:
                    pass
        except Exception:
            self._selected_items = []
        # notify
        if self.notify():
            try:
                dlg = self.findDialog()
                if dlg is not None:
                    dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
            except Exception:
                pass
