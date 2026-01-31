# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
"""
Python manatools.aui.backends.curses contains curses backend for YImage

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.curses
"""
import curses
import logging
import os
from ...yui_common import *

# Module-level logger for image curses backend
_mod_logger = logging.getLogger("manatools.aui.curses.image.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)


class YImageCurses(YWidget):
    def __init__(self, parent=None, imageFileName=""):
        super().__init__(parent)
        self._imageFileName = imageFileName
        self._auto_scale = False
        self._zero_size = {YUIDimension.YD_HORIZ: False, YUIDimension.YD_VERT: False}
        self._height = 3
        self._width = 10
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)
        self._logger.debug("%s.__init__ file=%s", self.__class__.__name__, imageFileName)

    def widgetClass(self):
        return "YImage"

    def imageFileName(self):
        return self._imageFileName

    def setImage(self, imageFileName):
        try:
            self._imageFileName = imageFileName
        except Exception:
            self._logger.exception("setImage failed")

    def autoScale(self):
        return bool(self._auto_scale)

    def setAutoScale(self, on=True):
        try:
            self._auto_scale = bool(on)
        except Exception:
            self._logger.exception("setAutoScale failed")

    def hasZeroSize(self, dim):
        return bool(self._zero_size.get(dim, False))

    def setZeroSize(self, dim, zeroSize=True):
        self._zero_size[dim] = bool(zeroSize)

    def _create_backend_widget(self):
        try:
            # nothing to create for curses; drawing uses _draw
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            self._logger.exception("_create_backend_widget failed")

    def _draw(self, window, y, x, width, height):
        if self._visible is False:
            return
        try:
            if width <= 0 or height <= 0:
                return
            # draw a box using box-drawing unicode characters
            try:
                horiz = '═'
                vert = '║'
                tl = '╔'
                tr = '╗'
                bl = '╚'
                br = '╝'
            except Exception:
                horiz = '-'
                vert = '|'
                tl = '+'
                tr = '+'
                bl = '+'
                br = '+'

            # top border
            try:
                window.addstr(y, x, tl + horiz * max(0, width - 2) + tr)
            except curses.error:
                pass
            # middle
            for row in range(1, max(0, height - 1)):
                try:
                    window.addstr(y + row, x, vert)
                    # fill space
                    try:
                        window.addstr(y + row, x + 1, ' ' * max(0, width - 2))
                    except curses.error:
                        pass
                    window.addstr(y + row, x + max(0, width - 1), vert)
                except curses.error:
                    pass
            # bottom border
            if height >= 2:
                try:
                    window.addstr(y + max(0, height - 1), x, bl + horiz * max(0, width - 2) + br)
                except curses.error:
                    pass

            # show filename centered (single line) if space
            if self._imageFileName:
                fname = os.path.basename(self._imageFileName)
                line = f" {fname} "
                if len(line) > max(0, width - 2):
                    line = line[:max(0, width - 5)] + '...'
                try:
                    cx = x + max(1, (width - len(line)) // 2)
                    cy = y + max(1, height // 2)
                    window.addstr(cy, cx, line)
                except curses.error:
                    pass
        except Exception:
            self._logger.exception("_draw failed")
