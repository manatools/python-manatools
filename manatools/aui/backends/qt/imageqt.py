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
        self._qicon = None
        # minimal visible size guard
        self._min_w = 64
        self._min_h = 32
        # aspect ratio tracking (w/h). default 1.0
        self._aspect_ratio = 1.0
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
                        self._qicon = ico
                        self._pixmap = None
                        # update aspect ratio from icon's largest available size
                        try:
                            sizes = ico.availableSizes()
                            if sizes:
                                s = max(sizes, key=lambda sz: sz.width()*sz.height())
                                self._aspect_ratio = max(0.0001, float(s.width()) / float(s.height() or 1))
                            else:
                                self._aspect_ratio = 1.0
                        except Exception:
                            self._aspect_ratio = 1.0
                        # re-apply constraints and redraw
                        self._apply_size_policy()
                        self._apply_pixmap()
                        return
                    except Exception:
                        pass

                # Fallback: try loading as pixmap from filesystem
                if os.path.exists(imageFileName):
                    try:
                        self._pixmap = QtGui.QPixmap(imageFileName)
                        # update aspect ratio from pixmap
                        try:
                            w = self._pixmap.width()
                            h = self._pixmap.height()
                            if w > 0 and h > 0:
                                self._aspect_ratio = max(0.0001, float(w) / float(h))
                        except Exception:
                            pass
                        # re-apply constraints and redraw
                        self._apply_size_policy()
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
            # Use a QLabel subclass with height-for-width to keep aspect ratio.
            class _ImageLabel(QtWidgets.QLabel):
                def __init__(self, owner, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self._owner = owner

                #def hasHeightForWidth(self):
                #    # Enable height-for-width only when autoscale is ON
                #    try:
                #        return bool(getattr(self._owner, "_auto_scale", False))
                #    except Exception:
                #        return False
#
                #def heightForWidth(self, w):
                #    try:
                #        ratio = max(0.0001, float(getattr(self._owner, "_aspect_ratio", 1.0)))
                #        h = int(max(self._owner._min_h, float(w) / ratio))
                #        return h
                #    except Exception:
                #        return super().heightForWidth(w)
#
                def resizeEvent(self, ev):
                    super().resizeEvent(ev)
                    try:
                        self._owner._apply_pixmap()
                    except Exception:
                        pass

                def sizeHint(self) -> QtCore.QSize:
                    """
                    Return the recommended size for the widget.
                    
                    This considers zero-size settings - if a dimension has zero size
                    enabled, it returns 0 for that dimension.
                    """
                    if self._owner._auto_scale:
                        # When auto-scaling, size hint depends on parent
                        return super().sizeHint()
                    
                    base_hint = super().sizeHint()

                    width = 0 if self._owner.stretchable(YUIDimension.YD_HORIZ) else base_hint.width()
                    height = 0 if self._owner.stretchable(YUIDimension.YD_VERT) else base_hint.height()
                    return QtCore.QSize(width, height)

                def minimumSizeHint(self) -> QtCore.QSize:
                    """
                    Return the minimum recommended size for the widget.
                    
                    This considers zero-size settings.
                    """
                    if self._owner._auto_scale:
                        # When auto-scaling, can shrink to 0
                        return QtCore.QSize(0, 0)
                    
                    base_hint = super().minimumSizeHint()
                    
                    width = 0 if self._owner.stretchable(YUIDimension.YD_HORIZ) else base_hint.width()
                    height = 0 if self._owner.stretchable(YUIDimension.YD_VERT) else base_hint.height()
                    
                    return QtCore.QSize(width, height)

            self._backend_widget = _ImageLabel(self)
            self._backend_widget.setAlignment(QtCore.Qt.AlignCenter)
            # enforce a small minimum so it never vanishes
            try:
                self._backend_widget.setMinimumSize(self._min_w, self._min_h)
            except Exception:
                pass
            if self._imageFileName:
                try:
                    self.setImage(self._imageFileName)
                except Exception:
                    # Fallback: try direct filesystem load
                    try:
                        if os.path.exists(self._imageFileName):
                            self._pixmap = QtGui.QPixmap(self._imageFileName)
                            self._apply_size_policy()
                            self._apply_pixmap()
                    except Exception:
                        pass
            self._apply_size_policy()
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            self._logger.exception("_create_backend_widget failed")

    def _apply_size_policy(self):
        try:
            if getattr(self, '_backend_widget', None) is None:
                return
            
            if self._auto_scale:
                self._backend_widget.setScaledContents(False)                
                # When auto-scaling, maintain aspect ratio by default
                self._backend_widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, 
                                QtWidgets.QSizePolicy.Policy.Expanding)
            else:
                self._backend_widget.setScaledContents(True)
                # Respect stretch flags; in autoscale allow height-for-width by not fixing vertical
                horiz = QtWidgets.QSizePolicy.Expanding if self.stretchable(YUIDimension.YD_HORIZ) else QtWidgets.QSizePolicy.Fixed
                vert = QtWidgets.QSizePolicy.Expanding if self.stretchable(YUIDimension.YD_VERT) else QtWidgets.QSizePolicy.Fixed
                try:
                    sp = self._backend_widget.sizePolicy()
                    sp.setHorizontalPolicy(horiz)
                    sp.setVerticalPolicy(vert)
                    self._backend_widget.setSizePolicy(sp)
                except Exception:
                    self._logger.exception("_apply_size_policy: setSizePolicy failed")

                # Reset caps: in autoscale mode allow full growth in both axes.
                try:
                    QWIDGETSIZE_MAX = getattr(QtWidgets, "QWIDGETSIZE_MAX", 16777215)
                    if self._auto_scale:
                        self._backend_widget.setMaximumWidth(QWIDGETSIZE_MAX)
                        self._backend_widget.setMaximumHeight(QWIDGETSIZE_MAX)
                    else:
                        # Non-autoscale: cap non-stretch axes to source size or a sane default
                        pm_w = pm_h = None
                        if isinstance(getattr(self, "_pixmap", None), QtGui.QPixmap) and not self._pixmap.isNull():
                            pm_w, pm_h = self._pixmap.width(), self._pixmap.height()
                        elif getattr(self, "_qicon", None) is not None:
                            pm_w, pm_h = 64, 64
                        if self.stretchable(YUIDimension.YD_HORIZ):
                            self._backend_widget.setMaximumWidth(QWIDGETSIZE_MAX)
                        else:
                            if pm_w:
                                self._backend_widget.setMaximumWidth(max(self._backend_widget.maximumWidth(), pm_w))
                        if self.stretchable(YUIDimension.YD_VERT):
                            self._backend_widget.setMaximumHeight(QWIDGETSIZE_MAX)
                        else:
                            if pm_h:
                                self._backend_widget.setMaximumHeight(max(self._backend_widget.maximumHeight(), pm_h))
                except Exception:
                    self._logger.exception("_apply_size_policy: max size tuning failed")

                # Keep a small minimum visible size
                try:
                    self._backend_widget.setMinimumSize(self._min_w, self._min_h)
                except Exception:
                    pass
        except Exception:
            self._logger.exception("_apply_size_policy failed")

    def _apply_pixmap(self):
        try:
            if getattr(self, '_backend_widget', None) is None:
                return
            size = self._backend_widget.size()
            if not size.isValid():
                size = QtCore.QSize(self._min_w, self._min_h)

            src_icon = self._qicon
            src_pm = self._pixmap if isinstance(self._pixmap, QtGui.QPixmap) and not self._pixmap.isNull() else None

            # AutoScale ON => keep aspect ratio to widget size (height-for-width will grow height as width grows)
            if self._auto_scale:
                # compute target size from current width and aspect ratio; clamp to widget size
                try:
                    ratio = max(0.0001, float(self._aspect_ratio))
                except Exception:
                    ratio = 1.0
                target_w = max(1, size.width())
                target_h = int(max(self._min_h, target_w / ratio))
                target_h = min(target_h, size.height())

                if src_icon is not None:
                    pm = src_icon.pixmap(QtCore.QSize(target_w, target_h))
                    if pm and not pm.isNull():
                        self._backend_widget.setPixmap(pm)
                        return
                if src_pm is not None:
                    scaled = src_pm.scaled(QtCore.QSize(target_w, target_h), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    self._backend_widget.setPixmap(scaled)
                else:
                    self._backend_widget.clear()
                return

            # AutoScale OFF => stretch along selected dimensions, allow deformation
            target_w = size.width()  if self.stretchable(YUIDimension.YD_HORIZ) else (src_pm.width() if src_pm else self._min_w)
            target_h = size.height() if self.stretchable(YUIDimension.YD_VERT)  else (src_pm.height() if src_pm else self._min_h)
            target_w = max(1, target_w)
            target_h = max(1, target_h)

            if src_icon is not None:
                pm = src_icon.pixmap(QtCore.QSize(target_w, target_h))
                if pm and not pm.isNull():
                    self._backend_widget.setPixmap(pm)
                    return

            if src_pm is not None:
                scaled = src_pm.scaled(target_w, target_h, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
                self._backend_widget.setPixmap(scaled)
            else:
                self._backend_widget.clear()
        except Exception:
            self._logger.exception("_apply_pixmap failed")

    def setStretchable(self, dim, new_stretch):
        try:
            super().setStretchable(dim, new_stretch)
        except Exception:
            pass
        try:
            self._apply_size_policy()
            self._apply_pixmap()
        except Exception:
            pass
