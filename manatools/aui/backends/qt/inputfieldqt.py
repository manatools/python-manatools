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
        if self._help_text:
            self._entry_widget.setToolTip(self._help_text)

        # Apply initial stretch policy
        try:
            self._apply_stretch_policy()
        except Exception:
            pass
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def setHelpText(self, help_text: str):
        super().setHelpText(help_text)
        try:
            if getattr(self, "_entry_widget", None) is not None:
                self._entry_widget.setToolTip(help_text)
        except Exception:
            self._logger.exception("setHelpText failed", exc_info=True)

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
        if not hasattr(self, '_entry_widget') or self._entry_widget is None:
            return

        horiz = bool(self.stretchable(YUIDimension.YD_HORIZ))
        vert = bool(self.stretchable(YUIDimension.YD_VERT))

        # Width: derived from font char width
        try:
            char_w = self._entry_widget.fontMetrics().horizontalAdvance('M')
            if char_w <= 0:
                char_w = 8
        except Exception:
            char_w = 8

        desired_chars = 20
        w_px = int(char_w * desired_chars) + 12

        # Height: use actual widget sizeHints so that border/padding of QLineEdit
        # and the real layout spacing are accounted for.
        # BUG FIXED: the old formula used fm.lineSpacing() (font metric only, ~17px)
        # instead of entry.sizeHint().height() (~28px with borders), and used
        # self._qlbl.isVisible() which returns False before the dialog is shown,
        # causing the container to be set too short and the cursor to appear at
        # the bottom of a squished entry box.
        try:
            entry_h = self._entry_widget.sizeHint().height()
            if entry_h <= 0:
                entry_h = 28
        except Exception:
            entry_h = 28

        # Use _label string (not isVisible) to determine if label row is present.
        # isVisible() returns False on a not-yet-shown widget even when no hide()
        # was called, producing qlabel_h=0 and a 25px container that clips the entry.
        has_label = bool(getattr(self, '_label', ''))
        try:
            if has_label:
                label_h = self._qlbl.sizeHint().height()
                if label_h <= 0:
                    label_h = 16
                try:
                    lay_spacing = self._backend_widget.layout().spacing()
                    if lay_spacing < 0:
                        lay_spacing = 6
                except Exception:
                    lay_spacing = 6
                h_px = label_h + lay_spacing + entry_h
            else:
                h_px = entry_h
        except Exception:
            h_px = entry_h

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
