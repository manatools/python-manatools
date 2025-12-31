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
        try:
            # If vertical stretch disabled, ensure minimal height equals default visible lines
            if dim == YUIDimension.YD_VERT:
                if not self.stretchable(YUIDimension.YD_VERT):
                    self._height = self._default_visible_lines + (1 if bool(self._label) else 0)
                    # apply fixed widget size (approximate width for 20 chars)
                    try:
                        if self._qwidget is not None:
                            fm = self._qtext.fontMetrics()
                            char_w = fm.horizontalAdvance('M') if fm is not None else 8
                            line_h = fm.lineSpacing() if fm is not None else 16
                            desired_chars = 20
                            w_px = int(char_w * desired_chars) + 12
                            h_px = int(line_h * self._default_visible_lines) + self._qlbl.sizeHint().height() + 8
                            self._qwidget.setFixedSize(w_px, h_px)
                            self._qtext.setFixedHeight(int(line_h * self._default_visible_lines))
                            self._qwidget.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
                    except Exception:
                        pass
                else:
                    # make widget expandable
                    try:
                        if self._qwidget is not None:
                            try:
                                self._qwidget.setMaximumSize(QtCore.QSize(16777215, 16777215))
                            except Exception:
                                pass
                            try:
                                self._qwidget.setMinimumSize(QtCore.QSize(0, 0))
                            except Exception:
                                pass
                            self._qwidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
                    except Exception:
                        pass
        except Exception:
            pass

    def _apply_stretch_policy(self):
        """Apply current stretchable flags to the created Qt widgets.

        When vertical/horizontal stretch is disabled we enforce a fixed size
        approximating 3 lines x 20 characters; when enabled we allow expanding.
        """
        try:
            if self._qwidget is None:
                return
            # horizontal and vertical checks
            horiz = self.stretchable(YUIDimension.YD_HORIZ)
            vert = self.stretchable(YUIDimension.YD_VERT)
            if not vert or not horiz:
                # compute approximate pixel sizes
                try:
                    fm = self._qtext.fontMetrics()
                    char_w = fm.horizontalAdvance('M') if fm is not None else 8
                    line_h = fm.lineSpacing() if fm is not None else 16
                except Exception:
                    char_w = 8
                    line_h = 16
                desired_chars = 20
                w_px = int(char_w * desired_chars) + 12
                h_px = int(line_h * self._default_visible_lines) + (self._qlbl.sizeHint().height() if hasattr(self, '_qlbl') else 0) + 8
                try:
                    self._qwidget.setFixedSize(w_px, h_px)
                except Exception:
                    try:
                        self._qwidget.setMaximumSize(QtCore.QSize(w_px, h_px))
                    except Exception:
                        pass
                try:
                    self._qtext.setFixedHeight(int(line_h * self._default_visible_lines))
                except Exception:
                    pass
                try:
                    self._qwidget.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
                except Exception:
                    pass
            else:
                try:
                    self._qwidget.setMaximumSize(QtCore.QSize(16777215, 16777215))
                except Exception:
                    pass
                try:
                    self._qwidget.setMinimumSize(QtCore.QSize(0, 0))
                except Exception:
                    pass
                try:
                    self._qwidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding if horiz else QtWidgets.QSizePolicy.Fixed, 
                                                QtWidgets.QSizePolicy.Expanding if vert else QtWidgets.QSizePolicy.Fixed)
                except Exception:
                    pass
        except Exception:
            try:
                self._logger.exception("_apply_stretch_policy failed")
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
