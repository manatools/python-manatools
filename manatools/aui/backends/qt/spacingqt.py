# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Qt backend: YSpacing implementation using a lightweight QWidget.

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''
from PySide6 import QtWidgets, QtCore
import logging
from ...yui_common import *
from .commonqt import _resolve_icon


class YSpacingQt(YWidget):
    """Spacing/Stretch widget for Qt.

    Constructor arguments:
    - parent: containing widget
    - dim: `YUIDimension` — primary dimension where spacing applies
    - stretchable: bool — if True, the spacing expands in its primary dimension
    - size: float — spacing size in pixels (device units). When stretchable is True,
      this acts as a minimum size in the primary dimension. When False, the size is
      fixed in the primary dimension.

    Notes:
    - This widget is visually empty; it only reserves space.
    - Pixels are used as the unit to avoid ambiguity. Other backends convert as
      appropriate (e.g., curses maps pixels to character cells using a fixed ratio).
    """
    def __init__(self, parent=None, dim: YUIDimension = YUIDimension.YD_HORIZ, stretchable: bool = False, size: float = 0.0):
        super().__init__(parent)
        self._dim = dim
        self._stretchable = bool(stretchable)
        try:
            self._size_px = max(0, int(round(float(size))))
        except Exception:
            self._size_px = 0
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
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
        try:
            w = QtWidgets.QWidget()
            sp = w.sizePolicy()
            if self._dim == YUIDimension.YD_HORIZ:
                # horizontal spacing
                try:
                    if self._stretchable:
                        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding)
                        w.setMinimumWidth(self._size_px)
                    else:
                        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Fixed)
                        w.setFixedWidth(self._size_px)
                    # vertical should not force expansion
                    sp.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Preferred)
                except Exception:
                    pass
            else:
                # vertical spacing
                try:
                    if self._stretchable:
                        sp.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding)
                        w.setMinimumHeight(self._size_px)
                    else:
                        sp.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Fixed)
                        w.setFixedHeight(self._size_px)
                    sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Preferred)
                except Exception:
                    pass
            try:
                w.setSizePolicy(sp)
            except Exception:
                pass
            self._backend_widget = w
            self._backend_widget.setEnabled(bool(self._enabled))
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            try:
                self._logger.exception("Failed to create YSpacingQt backend")
            except Exception:
                pass
            self._backend_widget = QtWidgets.QWidget()

    def _set_backend_enabled(self, enabled):
        try:
            if self._backend_widget is not None:
                self._backend_widget.setEnabled(bool(enabled))
        except Exception:
            pass
