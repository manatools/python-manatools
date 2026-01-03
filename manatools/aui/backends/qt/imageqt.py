# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
"""
Python manatools.aui.backends.qt contains Qt backend for YImage

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
"""
from PySide6 import QtWidgets, QtGui, QtCore
import logging
import os
from ...yui_common import *
from .commonqt import _resolve_icon as _qt_resolve_icon


class YImageQt(YWidget):
    def __init__(self, parent=None, imageFileName=""):
        super().__init__(parent)
        self._imageFileName = imageFileName
        self._auto_scale = False
        self._zero_size = {YUIDimension.YD_HORIZ: False, YUIDimension.YD_VERT: False}
        self._pixmap = None
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        self._logger.debug("%s.__init__ file=%s", self.__class__.__name__, imageFileName)

    def widgetClass(self):
        return "YImage"

    def imageFileName(self):
        return self._imageFileName

    def setImage(self, imageFileName):
        try:
            self._imageFileName = imageFileName
            if getattr(self, '_backend_widget', None) is not None:
                # Try resolving via common Qt helper (theme icon or filesystem)
                try:
                    ico = _qt_resolve_icon(imageFileName)
                except Exception:
                    ico = None
                if ico is not None:
                    try:
                        # store QIcon and let _apply_pixmap pick appropriate size
                        self._qicon = ico
                        self._apply_pixmap()
                        return
                    except Exception:
                        pass

                # Fallback: try loading as pixmap from filesystem
                if os.path.exists(imageFileName):
                    try:
                        self._pixmap = QtGui.QPixmap(imageFileName)
                        self._apply_pixmap()
                    except Exception:
                        self._logger.exception("setImage: failed to load QPixmap %s", imageFileName)
                else:
                    self._logger.error("setImage: file not found: %s", imageFileName)
        except Exception:
            self._logger.exception("setImage failed")

    def autoScale(self):
        return bool(self._auto_scale)

    def setAutoScale(self, on=True):
        try:
            self._auto_scale = bool(on)
            # If autoscale is enabled, let Qt expand the widget when stretchable
            self._apply_size_policy()
            self._apply_pixmap()
        except Exception:
            self._logger.exception("setAutoScale failed")

    def hasZeroSize(self, dim):
        return bool(self._zero_size.get(dim, False))

    def setZeroSize(self, dim, zeroSize=True):
        self._zero_size[dim] = bool(zeroSize)
        try:
            self._apply_size_policy()
        except Exception:
            pass

    def _create_backend_widget(self):
        try:
            # Use a QLabel subclass that notifies this owner on resize so
            # we can re-apply scaled pixmaps when the widget changes size.
            class _ImageLabel(QtWidgets.QLabel):
                def __init__(self, owner, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self._owner = owner

                def resizeEvent(self, ev):
                    super().resizeEvent(ev)
                    try:
                        self._owner._apply_pixmap()
                    except Exception:
                        pass

                def sizeHint(self):
                    try:
                        # When autoscale is enabled prefer to give a small size hint
                        # so layouts can shrink the widget; actual pixmap will be
                        # scaled on resizeEvent.
                        if getattr(self._owner, '_auto_scale', False):
                            return QtCore.QSize(0, 0)
                    except Exception:
                        pass
                    return super().sizeHint()

                def minimumSizeHint(self):
                    try:
                        if getattr(self._owner, '_auto_scale', False):
                            return QtCore.QSize(0, 0)
                    except Exception:
                        pass
                    return super().minimumSizeHint()

            self._backend_widget = _ImageLabel(self)
            self._backend_widget.setAlignment(QtCore.Qt.AlignCenter)
            if self._imageFileName and os.path.exists(self._imageFileName):
                self._pixmap = QtGui.QPixmap(self._imageFileName)
                self._apply_pixmap()
            self._apply_size_policy()
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            self._logger.exception("_create_backend_widget failed")

    def _apply_size_policy(self):
        try:
            if getattr(self, '_backend_widget', None) is None:
                return
            horiz = QtWidgets.QSizePolicy.Policy.Expanding if self._auto_scale or self.stretchable(YUIDimension.YD_HORIZ) else QtWidgets.QSizePolicy.Policy.Fixed
            vert = QtWidgets.QSizePolicy.Policy.Expanding if self._auto_scale or self.stretchable(YUIDimension.YD_VERT) else QtWidgets.QSizePolicy.Policy.Fixed
            try:
                sp = self._backend_widget.sizePolicy()
                sp.setHorizontalPolicy(horiz)
                sp.setVerticalPolicy(vert)
                self._backend_widget.setSizePolicy(sp)
            except Exception:
                pass
        except Exception:
            self._logger.exception("_apply_size_policy failed")

    def _apply_pixmap(self):
        try:
            if getattr(self, '_backend_widget', None) is None:
                return
            if not self._pixmap:
                self._backend_widget.clear()
                return
            # If we have a QIcon (resolved from theme/name) prefer it as it can provide
            # appropriately scaled pixmaps. Otherwise use the stored QPixmap.
            try:
                if getattr(self, '_qicon', None) is not None:
                    if self._auto_scale and self._backend_widget.size().isValid():
                        pm = self._qicon.pixmap(self._backend_widget.size())
                    else:
                        pm = self._qicon.pixmap(64, 64)
                    if pm and not pm.isNull():
                        self._backend_widget.setPixmap(pm)
                        return
            except Exception:
                pass

            if self._pixmap:
                if self._auto_scale and self._backend_widget.width() > 1 and self._backend_widget.height() > 1:
                    scaled = self._pixmap.scaled(self._backend_widget.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    self._backend_widget.setPixmap(scaled)
                else:
                    self._backend_widget.setPixmap(self._pixmap)
        except Exception:
            self._logger.exception("_apply_pixmap failed")

    def setStretchable(self, dim, new_stretch):
        try:
            super().setStretchable(dim, new_stretch)
        except Exception:
            pass
        try:
            self._apply_size_policy()
        except Exception:
            pass
