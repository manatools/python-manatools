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


class YLogViewQt(YWidget):
    """Qt backend for YLogView using QPlainTextEdit in a container with an optional QLabel.
    - Stores log lines with optional max retention (storedLines==0 means unlimited).
    - Stretchable horizontally and vertically.
    - Public API mirrors libyui's YLogView: label, visibleLines, maxLines, appendLines, clearText, etc.
    """
    def __init__(self, parent=None, label: str = "", visibleLines: int = 10, storedLines: int = 0):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        self._label = label or ""
        self._visible = max(1, int(visibleLines or 10))
        self._max_lines = max(0, int(storedLines or 0))
        self._lines = []
        try:
            self.setStretchable(YUIDimension.YD_HORIZ, True)
            self.setStretchable(YUIDimension.YD_VERT, True)
        except Exception:
            pass

    def widgetClass(self):
        return "YLogView"

    # API
    def label(self) -> str:
        return self._label

    def setLabel(self, label: str):
        self._label = label or ""
        try:
            if getattr(self, "_label_widget", None) is not None:
                self._label_widget.setText(self._label)
        except Exception:
            self._logger.exception("setLabel failed")

    def visibleLines(self) -> int:
        return int(self._visible)

    def setVisibleLines(self, newVisibleLines: int):
        self._visible = max(1, int(newVisibleLines or 1))
        try:
            self._apply_preferred_height()
        except Exception:
            self._logger.exception("setVisibleLines apply height failed")

    def maxLines(self) -> int:
        return int(self._max_lines)

    def setMaxLines(self, newMaxLines: int):
        self._max_lines = max(0, int(newMaxLines or 0))
        self._trim_if_needed()
        self._update_display()

    def logText(self) -> str:
        return "\n".join(self._lines)

    def setLogText(self, text: str):
        try:
            raw = [] if text is None else str(text).splitlines()
            self._lines = raw
            self._trim_if_needed()
            self._update_display()
        except Exception:
            self._logger.exception("setLogText failed")

    def lastLine(self) -> str:
        return self._lines[-1] if self._lines else ""

    def appendLines(self, text: str):
        try:
            if text is None:
                return
            for ln in str(text).splitlines():
                self._lines.append(ln)
            self._trim_if_needed()
            self._update_display(scroll_end=True)
        except Exception:
            self._logger.exception("appendLines failed")

    def clearText(self):
        self._lines = []
        self._update_display()

    def lines(self) -> int:
        return len(self._lines)

    # Internals
    def _trim_if_needed(self):
        try:
            if self._max_lines > 0 and len(self._lines) > self._max_lines:
                self._lines = self._lines[-self._max_lines:]
        except Exception:
            self._logger.exception("trim failed")

    def _apply_preferred_height(self):
        try:
            if getattr(self, "_text", None) is not None:
                fm = self._text.fontMetrics()
                h = fm.lineSpacing() * (self._visible + 1)
                self._text.setMinimumHeight(h)
        except Exception:
            pass

    def _update_display(self, scroll_end: bool = False):
        try:
            if getattr(self, "_text", None) is not None:
                self._text.setPlainText("\n".join(self._lines))
                if scroll_end:
                    try:
                        self._text.moveCursor(self._text.textCursor().End)
                    except Exception:
                        pass
        except Exception:
            self._logger.exception("update_display failed")

    def _create_backend_widget(self):
        container = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        if self._label:
            lbl = QtWidgets.QLabel(self._label)
            self._label_widget = lbl
            lay.addWidget(lbl)
        txt = QtWidgets.QPlainTextEdit()
        txt.setReadOnly(True)
        try:
            txt.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        except Exception:
            pass
        sp = txt.sizePolicy()
        try:
            sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
            sp.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
        except Exception:
            pass
        txt.setSizePolicy(sp)
        lay.addWidget(txt)
        self._text = txt
        self._apply_preferred_height()
        self._update_display()
        self._backend_widget = container
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.setEnabled(bool(enabled))
        except Exception:
            pass
