# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains Qt backend for YMultiLineEdit

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''
import logging
from ...yui_common import *
try:
    from PySide6 import QtWidgets, QtCore
except Exception:
    QtWidgets = None
    QtCore = None

_mod_logger = logging.getLogger("manatools.aui.qt.multiline.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)


class YMultiLineEditQt(YWidget):
    def __init__(self, parent=None, label=""):
        super().__init__(parent)
        self._label = label
        self._value = ""
        # default visible content lines (consistent across backends)
        self._default_visible_lines = 3
        # -1 means no input length limit
        self._input_max_length = -1
        # reported minimal height: content lines + label row (if present)
        self._height = self._default_visible_lines + (1 if bool(self._label) else 0)
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        if not self._logger.handlers and _mod_logger.handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)

        self._qwidget = None

    def widgetClass(self):
        return "YMultiLineEdit"

    def value(self):
        return str(self._value)

    def inputMaxLength(self):
        return int(getattr(self, '_input_max_length', -1))

    def setInputMaxLength(self, numberOfChars):
        try:
            self._input_max_length = int(numberOfChars)
        except Exception:
            self._input_max_length = -1
        # enforce immediately on widget
        try:
            if self._qwidget is not None and self._input_max_length >= 0:
                txt = self._qtext.toPlainText()
                if len(txt) > self._input_max_length:
                    try:
                        self._qtext.blockSignals(True)
                        self._qtext.setPlainText(txt[:self._input_max_length])
                        self._qtext.blockSignals(False)
                        self._value = self._qtext.toPlainText()
                    except Exception:
                        pass
        except Exception:
            pass

    def setValue(self, text):
        try:
            s = str(text) if text is not None else ""
        except Exception:
            s = ""
        # enforce input max length if set
        try:
            if getattr(self, '_input_max_length', -1) >= 0 and len(s) > self._input_max_length:
                s = s[: self._input_max_length]
        except Exception:
            pass
        self._value = s
        try:
            if self._qwidget is not None:
                try:
                    self._qtext.setPlainText(self._value)
                except Exception:
                    pass
        except Exception:
            pass

    def defaultVisibleLines(self):
        return int(getattr(self, '_default_visible_lines', 3))

    def setDefaultVisibleLines(self, newVisibleLines):
        try:
            self._default_visible_lines = int(newVisibleLines)
            self._height = self._default_visible_lines + (1 if bool(self._label) else 0)
        except Exception:
            pass

    def label(self):
        return self._label

    def setLabel(self, label):
        try:
            self._label = label
            if self._qwidget is not None:
                try:
                    self._qlbl.setText(str(label))
                except Exception:
                    pass
        except Exception:
            pass

    def setStretchable(self, dim, new_stretch):
        try:
            super().setStretchable(dim, new_stretch)
        except Exception:
            pass
        # Re-apply policy so changes take effect immediately
        try:
            self._apply_stretch_policy()
        except Exception:
            pass

    def _apply_stretch_policy(self):
        """Apply current stretchable flags per axis without locking both dimensions."""
        if self._qwidget is None:
            return

        # Current flags
        horiz = bool(self.stretchable(YUIDimension.YD_HORIZ))
        vert = bool(self.stretchable(YUIDimension.YD_VERT))

        # Compute approximate pixel sizes (fallback to constants)
        try:
            fm = self._qtext.fontMetrics() if hasattr(self, '_qtext') and self._qtext is not None else None
            char_w = fm.horizontalAdvance('M') if fm is not None else 8
            line_h = fm.lineSpacing() if fm is not None else 16
        except Exception:
            char_w = 8
            line_h = 16

        desired_chars = 20
        try:
            qlabel_h = self._qlbl.sizeHint().height() if hasattr(self, '_qlbl') and self._qlbl is not None else 0
        except Exception:
            qlabel_h = 0

        w_px = int(char_w * desired_chars) + 12
        h_px = int(line_h * max(1, self._default_visible_lines)) + qlabel_h + 8

        # Set per-axis size policy
        try:
            self._qwidget.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding if horiz else QtWidgets.QSizePolicy.Fixed,
                QtWidgets.QSizePolicy.Expanding if vert else QtWidgets.QSizePolicy.Fixed,
            )
        except Exception:
            pass

        # Apply horizontal constraint independently
        try:
            if not horiz:
                try:
                    self._qwidget.setFixedWidth(w_px)
                except Exception:
                    try:
                        self._qwidget.setMaximumWidth(w_px)
                    except Exception:
                        pass
            else:
                try:
                    self._qwidget.setMinimumWidth(0)
                    self._qwidget.setMaximumWidth(16777215)
                except Exception:
                    pass
        except Exception:
            pass

        # Apply vertical constraint independently
        try:
            if not vert:
                try:
                    self._qwidget.setFixedHeight(h_px)
                except Exception:
                    try:
                        self._qwidget.setMaximumHeight(h_px)
                    except Exception:
                        pass
                try:
                    if hasattr(self, '_qtext') and self._qtext is not None:
                        self._qtext.setFixedHeight(int(line_h * max(1, self._default_visible_lines)))
                except Exception:
                    pass
            else:
                try:
                    self._qwidget.setMinimumHeight(0)
                    self._qwidget.setMaximumHeight(16777215)
                    if hasattr(self, '_qtext') and self._qtext is not None:
                        self._qtext.setMinimumHeight(0)
                        self._qtext.setMaximumHeight(16777215)
                except Exception:
                    pass
        except Exception:
            pass

    def _create_backend_widget(self):
        try:
            if QtWidgets is None:
                raise ImportError("PySide6 not available")
            self._qwidget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(self._qwidget)
            layout.setContentsMargins(0, 0, 0, 0)
            self._qlbl = QtWidgets.QLabel(str(self._label))
            self._qtext = QtWidgets.QPlainTextEdit()
            self._qtext.setPlainText(self._value)
            layout.addWidget(self._qlbl)
            layout.addWidget(self._qtext)
            # apply current stretchable policy state
            try:
                self._apply_stretch_policy()
            except Exception:
                pass
            try:
                self._qtext.textChanged.connect(self._on_text_changed)
            except Exception:
                pass
            self._backend_widget = self._qwidget
        except Exception as e:
            try:
                self._logger.exception("Error creating Qt MultiLineEdit backend: %s", e)
            except Exception:
                pass

    def _set_backend_enabled(self, enabled):
        try:
            if self._qwidget is not None:
                try:
                    self._qtext.setReadOnly(not enabled)
                except Exception:
                    pass
        except Exception:
            pass

    def _on_text_changed(self):
        try:
            text = self._qtext.toPlainText()
            # enforce input max length if set
            try:
                if getattr(self, '_input_max_length', -1) >= 0 and len(text) > self._input_max_length:
                    # truncate and restore cursor
                    cur = self._qtext.textCursor()
                    pos = cur.position()
                    self._qtext.blockSignals(True)
                    self._qtext.setPlainText(text[:self._input_max_length])
                    self._qtext.blockSignals(False)
                    self._value = self._qtext.toPlainText()
                    try:
                        cur.setPosition(min(pos, self._input_max_length))
                        self._qtext.setTextCursor(cur)
                    except Exception:
                        pass
                else:
                    self._value = text
            except Exception:
                self._value = text
            dlg = self.findDialog()
            if dlg is not None:
                try:
                    if self.notify():
                        dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
                except Exception:
                    try:
                        self._logger.exception("Failed to post ValueChanged event")
                    except Exception:
                        pass
        except Exception:
            try:
                self._logger.exception("_on_text_changed error")
            except Exception:
                pass
