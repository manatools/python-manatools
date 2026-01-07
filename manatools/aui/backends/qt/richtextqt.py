# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains all Qt backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''
from PySide6 import QtWidgets, QtCore, QtGui
import logging
from ...yui_common import *

class YRichTextQt(YWidget):
    """
    Rich text widget using Qt's QTextBrowser.
    - Supports plain text and rich HTML-like content.
    - Emits an Activated event on link clicks without navigating.
    - Optional auto-scroll on updates.
    """
    def __init__(self, parent=None, text: str = "", plainTextMode: bool = False):
        super().__init__(parent)
        self._text = text or ""
        self._plain = bool(plainTextMode)
        self._auto_scroll = False
        self._last_url = None
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        # Default: richtext is stretchable in both dimensions
        try:
            self.setStretchable(YUIDimension.YD_HORIZ, True)
            self.setStretchable(YUIDimension.YD_VERT, True)
        except Exception:
            pass

    def widgetClass(self):
        return "YRichText"

    # Value API
    def setValue(self, newValue: str):
        try:
            self._text = newValue or ""
        except Exception:
            self._text = ""
        try:
            if getattr(self, "_backend_widget", None) is not None:
                if self._plain:
                    try:
                        self._backend_widget.setPlainText(self._text)
                    except Exception:
                        self._backend_widget.setText(self._text)
                else:
                    try:
                        self._backend_widget.setHtml(self._text)
                    except Exception:
                        self._backend_widget.setText(self._text)
                if self._auto_scroll:
                    try:
                        cursor = self._backend_widget.textCursor()
                        cursor.movePosition(QtGui.QTextCursor.End)
                        self._backend_widget.setTextCursor(cursor)
                        self._backend_widget.ensureCursorVisible()
                    except Exception:
                        pass
        except Exception:
            pass

    def value(self) -> str:
        return self._text

    # Plain text mode
    def plainTextMode(self) -> bool:
        return bool(self._plain)

    def setPlainTextMode(self, on: bool = True):
        self._plain = bool(on)
        # refresh backend content to reflect mode
        self.setValue(self._text)

    # Auto scroll
    def autoScrollDown(self) -> bool:
        return bool(self._auto_scroll)

    def setAutoScrollDown(self, on: bool = True):
        self._auto_scroll = bool(on)
        # optional immediate effect
        if self._auto_scroll and getattr(self, "_backend_widget", None) is not None:
            try:
                cursor = self._backend_widget.textCursor()
                cursor.movePosition(QtGui.QTextCursor.End)
                self._backend_widget.setTextCursor(cursor)
                self._backend_widget.ensureCursorVisible()
            except Exception:
                pass

    # Link activation info
    def lastActivatedUrl(self):
        return self._last_url

    def _create_backend_widget(self):
        tb = QtWidgets.QTextBrowser()
        # Prevent navigation; we only emit events on link clicks
        try:
            tb.setOpenExternalLinks(False)
        except Exception:
            pass
        try:
            tb.setOpenLinks(False)
        except Exception:
            pass
        try:
            tb.setReadOnly(True)
        except Exception:
            pass
        # set initial content
        try:
            if self._plain:
                tb.setPlainText(self._text)
            else:
                tb.setHtml(self._text)
        except Exception:
            try:
                tb.setText(self._text)
            except Exception:
                pass
        # connect link activation
        def _on_anchor_clicked(url: QtCore.QUrl):
            try:
                self._last_url = url.toString()
            except Exception:
                self._last_url = None
            try:
                dlg = self.findDialog()
                if dlg and self.notify():
                    dlg._post_event(YMenuEvent( id=url.toString()) )
                    self._logger.debug("Link activated: %s", url.toString())
            except Exception:
                self._logger.error("Posting Link activated: %s", url.toString())
                pass
        try:
            tb.anchorClicked.connect(_on_anchor_clicked)
        except Exception:
            # fallback: try signal on QLabel-like
            try:
                tb.linkActivated.connect(lambda _u: _on_anchor_clicked(QtCore.QUrl(str(_u))))
            except Exception:
                pass
        # Encourage expansion when placed in layouts
        try:
            sp = tb.sizePolicy()
            try:
                sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Expanding)
                sp.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Expanding)
            except Exception:
                try:
                    sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
                    sp.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
                except Exception:
                    pass
            tb.setSizePolicy(sp)
        except Exception:
            pass
        self._backend_widget = tb
        # respect initial enabled state
        try:
            self._backend_widget.setEnabled(bool(self._enabled))
        except Exception:
            pass
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
