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

class YAlignmentQt(YSingleChildContainerWidget):
    """
    Single-child alignment container for Qt6. Uses a QWidget + QGridLayout,
    applying Qt.Alignment flags to the child. The container expands along
    axes needed by Right/HCenter/VCenter/HVCenter to allow alignment.
    """
    def __init__(self, parent=None, horAlign: YAlignmentType=YAlignmentType.YAlignUnchanged, vertAlign: YAlignmentType=YAlignmentType.YAlignUnchanged):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        self._halign_spec = horAlign
        self._valign_spec = vertAlign
        self._backend_widget = None
        self._layout = None

    def widgetClass(self):
        return "YAlignment"

    def _to_qt_halign(self):
        """Convert Horizontal YAlignmentType to QtCore.Qt.AlignmentFlag or None."""        
        if self._halign_spec:
            if self._halign_spec == YAlignmentType.YAlignBegin:
                return QtCore.Qt.AlignmentFlag.AlignLeft
            if self._halign_spec == YAlignmentType.YAlignCenter:
                return QtCore.Qt.AlignmentFlag.AlignHCenter
            if self._halign_spec == YAlignmentType.YAlignEnd:
                return QtCore.Qt.AlignmentFlag.AlignRight
        return None
    
    def _to_qt_valign(self):
        """Convert Vertical YAlignmentType to QtCore.Qt.AlignmentFlag or None."""        
        if self._valign_spec:
            if self._valign_spec == YAlignmentType.YAlignBegin:
                return QtCore.Qt.AlignmentFlag.AlignTop
            if self._valign_spec == YAlignmentType.YAlignCenter:
                return QtCore.Qt.AlignmentFlag.AlignVCenter
            if self._valign_spec == YAlignmentType.YAlignEnd:
                return QtCore.Qt.AlignmentFlag.AlignBottom
        return None


    def stretchable(self, dim: YUIDimension):
        ''' Returns the stretchability of the layout box:
          * The layout box is stretchable if the alignment spec requests expansion
          * (Right/HCenter/HVCenter for horizontal, VCenter/HVCenter for vertical)
          * OR if the child itself requests stretchability or has a layout weight.
        '''
        # Expand if alignment spec requests it
        try:
            if dim == YUIDimension.YD_HORIZ:
                if self._halign_spec in (YAlignmentType.YAlignEnd, YAlignmentType.YAlignCenter):
                    return True
            if dim == YUIDimension.YD_VERT:
                if self._valign_spec in (YAlignmentType.YAlignCenter,):
                    return True
        except Exception:
            pass

        # Otherwise honor child's own stretchability/weight
        try:
            if self.child():
                expand = bool(self.child().stretchable(dim))
                weight = bool(self.child().weight(dim))
                if expand or weight:
                    return True
        except Exception:
            pass
        return False

    def setAlignment(self, horAlign: YAlignmentType=YAlignmentType.YAlignUnchanged, vertAlign: YAlignmentType=YAlignmentType.YAlignUnchanged):
        self._halign_spec = horAlign
        self._valign_spec = vertAlign
        self._reapply_alignment()

    def _reapply_alignment(self):
        if not (self._layout and self.child()):
            return
        try:
            w = self.child().get_backend_widget()
            if w:
                self._layout.removeWidget(w)
                flags = QtCore.Qt.AlignmentFlag(0)
                ha = self._to_qt_halign()
                va = self._to_qt_valign()
                if ha:
                    flags |= ha
                if va:
                    flags |= va
                self._layout.addWidget(w, 0, 0, flags)
        except Exception:
            pass

    def addChild(self, child):
        super().addChild(child)
        self._attach_child_backend()


    def _attach_child_backend(self):
        if not (self._backend_widget and self._layout and self.child()):
            return
        try:
            w = self.child().get_backend_widget()
            if w:
                # clear previous
                try:
                    self._layout.removeWidget(w)
                except Exception:
                    pass
                flags = QtCore.Qt.AlignmentFlag(0)
                ha = self._to_qt_halign()
                va = self._to_qt_valign()
                if ha:
                    flags |= ha
                if va:
                    flags |= va
                # If the child requests horizontal stretch, set its QSizePolicy to Expanding
                try:
                    if self.child() and self.child().stretchable(YUIDimension.YD_HORIZ):
                        sp = w.sizePolicy()
                        try:
                            sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Expanding)
                        except Exception:
                            try:
                                sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
                            except Exception:
                                pass
                        w.setSizePolicy(sp)
                    # If child requests vertical stretch, set vertical policy
                    if self.child() and self.child().stretchable(YUIDimension.YD_VERT):
                        sp = w.sizePolicy()
                        try:
                            sp.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Expanding)
                        except Exception:
                            try:
                                sp.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
                            except Exception:
                                pass
                        w.setSizePolicy(sp)
                except Exception:
                    pass
                self._layout.addWidget(w, 0, 0, flags)
        except Exception:
            pass

    def _create_backend_widget(self):
        container = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)

        # Size policy: expand along axes needed for alignment to work
        sp = container.sizePolicy()
        try: 
            sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Expanding if self.stretchable(YUIDimension.YD_HORIZ)
                                   else QtWidgets.QSizePolicy.Policy.Fixed)
            sp.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Expanding if self.stretchable(YUIDimension.YD_VERT)
                                 else QtWidgets.QSizePolicy.Policy.Fixed)
        except Exception:
            pass
        container.setSizePolicy(sp)

        self._backend_widget = container
        self._layout = grid
        self._backend_widget.setEnabled(bool(self._enabled))

        if self.hasChildren():
            self._attach_child_backend()
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        """Enable/disable the alignment container and propagate to its logical child."""
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass
        # propagate to logical child
        try:
            child = self.child()
            if child is not None:
                try:
                    child.setEnabled(enabled)
                except Exception:
                    pass
        except Exception:
            pass
