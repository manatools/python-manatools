# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Curses backend: YSpacing implementation as a non-drawing spacer.

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.curses
'''
import logging
from ...yui_common import *
from .commoncurses import pixels_to_chars


class YSpacingCurses(YWidget):
    """Spacing/Stretch widget for curses.

    - `dim`: primary dimension where spacing applies
    - `stretchable`: if True, the spacing expands in its primary dimension
    - `size`: spacing size expressed in pixels; converted to character cells
      using the libyui 800x600→80x25 mapping (10 px/col, 24 px/row).
    """
    def __init__(self, parent=None, dim: YUIDimension = YUIDimension.YD_HORIZ, stretchable: bool = False, size_px: int = 0):
        super().__init__(parent)
        self._dim = dim
        self._stretchable = bool(stretchable)
        try:
            spx = int(size_px)
            self._size_px = 0 if spx <= 0 else max(1, spx)
        except Exception:
            self._size_px = 0
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        # Sync base stretch flags so containers can query stretchable()
        try:
            self.setStretchable(self._dim, self._stretchable)
        except Exception:
            pass
        try:
            self._logger.debug("%s.__init__(dim=%s, stretchable=%s, size_px=%d)", self.__class__.__name__, self._dim, self._stretchable, self._size_px)
        except Exception:
            pass

    def widgetClass(self):
        return "YSpacing"

    def dimension(self):
        return self._dim

    def size(self):
        return self._size_px

    def sizeDim(self, dim: YUIDimension):
        return self._size_px if dim == self._dim else 0

    def _create_backend_widget(self):
        # curses uses logical widget; no separate backend structure required
        self._backend_widget = self
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def _desired_height_for_width(self, width):
        try:
            if self._dim == YUIDimension.YD_VERT:
                return pixels_to_chars(self._size_px, YUIDimension.YD_VERT)
        except Exception:
            pass
        return 0

    def minWidth(self):
        try:
            if self._dim == YUIDimension.YD_HORIZ:
                return pixels_to_chars(self._size_px, YUIDimension.YD_HORIZ)
        except Exception:
            pass
        return 0

    def _draw(self, window, y, x, width, height):
        # spacing draws nothing; reserved area remains blank
        return
