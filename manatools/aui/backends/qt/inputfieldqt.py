# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains all Qt backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''
from PySide6 import QtWidgets, QtCore
import logging
from ...yui_common import *

class YInputFieldQt(YWidget):
    def __init__(self, parent=None, label="", password_mode=False):
        super().__init__(parent)
        self._label = label
        self._value = ""
        self._password_mode = password_mode
        self._input_max_length = -1
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
    
    def widgetClass(self):
        return "YInputField"
    
    def value(self):
        return self._value
    
    def inputMaxLength(self):
        return int(getattr(self, '_input_max_length', -1))

    def setInputMaxLength(self, numberOfChars):
        try:
            self._input_max_length = int(numberOfChars)
        except Exception:
            self._input_max_length = -1
        if self._password_mode:
            return
        try:
            if getattr(self, '_entry_widget', None) is not None:
                max_len = self._input_max_length if self._input_max_length >= 0 else 2147483647
                self._entry_widget.setMaxLength(max_len)
                if self._input_max_length >= 0:
                    current = self._entry_widget.text()
                    if len(current) > self._input_max_length:
                        try:
                            self._entry_widget.blockSignals(True)
                            self._entry_widget.setText(current[:self._input_max_length])
                            self._entry_widget.blockSignals(False)
                            self._value = self._entry_widget.text()
                        except Exception:
                            pass
        except Exception:
            pass

    def setValue(self, text):
        s = text if text is not None else ""
        if not self._password_mode and getattr(self, '_input_max_length', -1) >= 0:
            s = s[:self._input_max_length]
        self._value = s
        if hasattr(self, '_entry_widget') and self._entry_widget:
            self._entry_widget.setText(self._value)
    
    def label(self):
        return self._label
    
    def _create_backend_widget(self):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self._qlbl = QtWidgets.QLabel(self._label)
        layout.addWidget(self._qlbl)
        if not self._label:
            self._qlbl.hide()

        entry = QtWidgets.QLineEdit()
        if self._password_mode:
            entry.setEchoMode(QtWidgets.QLineEdit.Password)

        entry.setText(self._value)
        entry.textChanged.connect(self._on_text_changed)
        if not self._password_mode and self._input_max_length >= 0:
            entry.setMaxLength(self._input_max_length)
        layout.addWidget(entry)

        self._backend_widget = container
        self._entry_widget = entry
        self._backend_widget.setEnabled(bool(self._enabled))

        # Apply initial stretch policy
        try:
            self._apply_stretch_policy()
        except Exception:
            pass
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        """Enable/disable the input field: entry and container."""
        try:
            if getattr(self, "_entry_widget", None) is not None:
                try:
                    self._entry_widget.setEnabled(bool(enabled))
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

    def _on_text_changed(self, text):
        self._value = text
        # Post ValueChanged when notify is enabled
        try:
            dlg = self.findDialog()
            if dlg is not None and self.notify():
                dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
        except Exception:
            pass

    def setLabel(self, label):
        self._label = label
        try:
            if hasattr(self, '_qlbl') and self._qlbl is not None:
                self._qlbl.setText(str(label))
                if not label:
                    self._qlbl.hide()
                else:
                    self._qlbl.show()
        except Exception:
            pass

    def setStretchable(self, dim, new_stretch):
        try:
            super().setStretchable(dim, new_stretch)
        except Exception:
            pass
        try:
            self._apply_stretch_policy()
        except Exception:
            pass

    def _apply_stretch_policy(self):
        """Apply independent horizontal/vertical stretch policies for single-line input."""
        if not hasattr(self, '_backend_widget') or self._backend_widget is None:
            return

        horiz = bool(self.stretchable(YUIDimension.YD_HORIZ))
        vert = bool(self.stretchable(YUIDimension.YD_VERT))

        # Compute approximate metrics
        try:
            fm = self._entry_widget.fontMetrics() if hasattr(self, '_entry_widget') else None
            char_w = fm.horizontalAdvance('M') if fm is not None else 8
            line_h = fm.lineSpacing() if fm is not None else 18
        except Exception:
            char_w, line_h = 8, 18

        desired_chars = 20
        try:
            # Only include the label height when the label is actually visible.
            # A hidden QLabel still has a positive sizeHint().height() (= font
            # line height ≈ 16–18 px), so blindly adding qlabel_h would make the
            # container ~44 px tall instead of ~26 px, causing the HBox search
            # bar row to be too tall and other widgets (comboboxes, checkbox) to
            # appear misaligned within that oversized row.
            label_visible = (
                hasattr(self, '_qlbl')
                and self._qlbl is not None
                and self._qlbl.isVisible()
            )
            qlabel_h = (
                self._qlbl.sizeHint().height()
                if label_visible
                else 0
            )
        except Exception:
            qlabel_h = 0

        w_px = int(char_w * desired_chars) + 12
        h_px = int(line_h) + qlabel_h + 8

        # Policy per axis
        try:
            self._backend_widget.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding if horiz else QtWidgets.QSizePolicy.Fixed,
                QtWidgets.QSizePolicy.Expanding if vert else QtWidgets.QSizePolicy.Fixed,
            )
        except Exception:
            pass

        # Width constraint
        try:
            if not horiz:
                self._backend_widget.setFixedWidth(w_px)
            else:
                self._backend_widget.setMinimumWidth(w_px)
                self._backend_widget.setMaximumWidth(16777215)
        except Exception:
            pass

        # Height constraint
        try:
            if not vert:
                self._backend_widget.setFixedHeight(h_px)
            else:
                self._backend_widget.setMinimumHeight(0)
                self._backend_widget.setMaximumHeight(16777215)
        except Exception:
            pass
