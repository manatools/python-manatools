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

    Parameters
    ----------
    parent : YWidget, optional
        Parent widget in the AUI hierarchy.
    label : str
        Optional caption drawn above the text area.
    visibleLines : int
        Minimum number of text rows shown (governs the preferred height).
    storedLines : int
        Maximum number of lines retained in memory (0 = unlimited).
    focus : YLogViewFocus
        Scroll-focus policy:

        * ``YLogViewFocus.HEAD`` *(default)* — viewport stays at the first
          line; :meth:`appendLines` does **not** scroll automatically.
        * ``YLogViewFocus.TAIL`` — viewport follows the last line; every
          call to :meth:`appendLines` scrolls to the bottom so the
          freshest content is always visible.
    reverse : bool
        When ``True`` the display order is **newest-first**: the line most
        recently appended appears at the *top* of the widget and older
        lines are pushed downward.  ``False`` (default) keeps the natural
        insertion order (oldest at top, newest at bottom).
    """
    def __init__(self, parent=None, label: str = "", visibleLines: int = 10,
                 storedLines: int = 0, focus: 'YLogViewFocus' = None,
                 reverse: bool = False):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        self._label = label or ""
        self._visible = max(1, int(visibleLines or 10))
        self._max_lines = max(0, int(storedLines or 0))
        self._lines = []
        # Resolve focus default lazily to avoid a circular import at module level.
        if focus is None:
            focus = YLogViewFocus.HEAD
        self._focus = focus
        self._reverse = bool(reverse)
        self._logger.debug(
            "YLogViewQt init: focus=%s reverse=%s", self._focus, self._reverse)
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
        """Append one or more lines to the log.

        ``self._lines`` is **always** kept in chronological order (oldest at
        index 0, newest at index ``-1``).  The *reverse* flag only controls
        how the lines are rendered in :meth:`_update_display`; it never
        changes the storage order.

        Automatic scrolling is controlled by :attr:`_focus`:

        * ``TAIL`` → scroll to the bottom of the rendered text (which is the
          newest line in normal mode, and the oldest line in reverse mode).
        * ``HEAD`` → no automatic scroll; the viewport stays where it is.
        """
        try:
            if text is None:
                return
            new_lines = str(text).splitlines()
            self._lines.extend(new_lines)
            self._trim_if_needed()
            scroll_end = (self._focus == YLogViewFocus.TAIL)
            self._logger.debug(
                "appendLines: added %d line(s), scroll_end=%s", len(new_lines), scroll_end)
            self._update_display(scroll_end=scroll_end)
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

    def focus(self) -> 'YLogViewFocus':
        """Return the current scroll-focus policy."""
        return self._focus

    def setFocus(self, focus: 'YLogViewFocus'):
        """Change the scroll-focus policy at runtime."""
        self._focus = focus
        self._logger.debug("setFocus: %s", focus)

    def reverse(self) -> bool:
        """Return whether newest-first display order is active."""
        return self._reverse

    def setReverse(self, reverse: bool):
        """Toggle newest-first display order and refresh the view.

        Only the *display* direction is changed; ``self._lines`` is always
        kept in chronological order and is never mutated here.
        """
        self._reverse = bool(reverse)
        self._logger.debug("setReverse: %s", self._reverse)
        self._update_display()

    def _update_display(self, scroll_end: bool = False):
        """Refresh the backend QPlainTextEdit from ``self._lines``.

        ``self._lines`` is always chronological (oldest first).  When
        *reverse* is ``True`` the text is built with
        ``reversed(self._lines)`` so the newest line appears at the **top**
        of the QPlainTextEdit and the oldest at the **bottom**.

        When *scroll_end* is ``True`` the vertical scrollbar is moved to
        ``maximum()`` — i.e. the **bottom of the rendered text** — regardless
        of *reverse*:

        * **normal order** — bottom = newest line (TAIL follows new events).
        * **reverse order** — bottom = oldest line (TAIL keeps the oldest
          content visible; this is the geometrical mirror of HEAD+normal).

        The scrollbar is manipulated directly (``verticalScrollBar()``) rather
        than via ``moveCursor`` because ``QTextCursor`` lives in ``QtGui``,
        not ``QtCore``.
        """
        try:
            if getattr(self, "_text", None) is not None:
                text = (
                    "\n".join(reversed(self._lines))
                    if self._reverse
                    else "\n".join(self._lines)
                )
                self._text.setPlainText(text)
                if scroll_end:
                    sb = self._text.verticalScrollBar()
                    sb.setValue(sb.maximum())
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
        # Respect the focus policy: if lines were already added before the
        # backend widget was built (the common case when appendLines is called
        # on a freshly-created widget before the dialog is shown), we must
        # re-play the initial scroll so TAIL views start at the bottom.
        self._update_display(scroll_end=(self._focus == YLogViewFocus.TAIL))
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
