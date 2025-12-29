# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.curses contains all curses backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.curses
'''
import logging
from ...yui_common import *

# Module-level logger for curses replace point backend
_mod_logger = logging.getLogger("manatools.aui.curses.replacepoint.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)

class YReplacePointCurses(YSingleChildContainerWidget):
    """
    NCurses backend implementation of YReplacePoint.

    A single-child placeholder; showChild() ensures the current child will
    be drawn in the curses UI, and deleteChildren() clears the logical model
    so a new child can be added later.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._backend_widget = self  # curses backends often use self as the drawable
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        try:
            self._logger.debug("%s.__init__", self.__class__.__name__)
        except Exception:
            pass

    def widgetClass(self):
        return "YReplacePoint"

    def _create_backend_widget(self):
        # No separate widget for curses: keep self as the drawable entity
        try:
            self._backend_widget = self
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception as e:
            try:
                self._logger.error("_create_backend_widget error: %s", e, exc_info=True)
            except Exception:
                pass

    def stretchable(self, dim: YUIDimension):
        """Propagate stretchability from the single child to the container."""
        try:
            ch = self.child()
            if ch is None:
                return False
            try:
                if bool(ch.stretchable(dim)):
                    return True
            except Exception:
                pass
            try:
                if bool(ch.weight(dim)):
                    return True
            except Exception:
                pass
        except Exception:
            pass
        return False

    def _set_backend_enabled(self, enabled):
        # Propagate enabled state to child if present
        try:
            ch = self.child()
            if ch is not None and hasattr(ch, "setEnabled"):
                ch.setEnabled(enabled)
        except Exception as e:
            try:
                self._logger.error("_set_backend_enabled error: %s", e, exc_info=True)
            except Exception:
                pass

    def addChild(self, child):
        super().addChild(child)
        try:
            self.showChild()
        except Exception:
            pass

    def showChild(self):
        """
        For curses, showing the child means ensuring the child will be drawn
        when this container's _draw is invoked. No further action is needed
        beyond the logical association, but this method exists for API parity
        and debugging.
        """
        try:
            self._logger.debug("showChild: child=%s", getattr(self.child(), "widgetClass", lambda: "?")())
            # Force dialog redraw on next loop iteration (similar to recalcLayout)
            try:
                dlg = self.findDialog()
                if dlg is not None:
                    try:
                        dlg._last_draw_time = 0
                    except Exception:
                        pass
                # Update minimal height to reflect child's needs
                try:
                    from .commoncurses import _curses_recursive_min_height
                    ch = self.child()
                    inner_min = _curses_recursive_min_height(ch) if ch is not None else 1
                    self._height = max(1, inner_min)
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass

    def deleteChildren(self):
        try:
            super().deleteChildren()
        except Exception as e:
            try:
                self._logger.error("deleteChildren error: %s", e, exc_info=True)
            except Exception:
                pass

    def _draw(self, window, y, x, width, height):
        """Delegate drawing to the single child if present."""
        try:
            ch = self.child()
            if ch is None:
                return
            if hasattr(ch, "_draw"):
                ch._draw(window, y, x, width, height)
        except Exception:
            pass
