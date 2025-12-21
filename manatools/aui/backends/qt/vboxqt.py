# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains all Qt backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''
from PySide6 import QtWidgets
import logging
from ...yui_common import *

class YVBoxQt(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
    
    def widgetClass(self):
        return "YVBox"

    # Returns the stretchability of the layout box:
    #  * The layout box is stretchable if one of the children is stretchable in
    #  * this dimension or if one of the child widgets has a layout weight in
    #  * this dimension.
    def stretchable(self, dim):
        for child in self._children:
            widget = child.get_backend_widget()
            expand = bool(child.stretchable(dim))
            weight = bool(child.weight(dim))
            if expand or weight:
                return True
        # No child is stretchable in this dimension
        return False

    def _create_backend_widget(self):
        self._backend_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self._backend_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        for child in self._children:
            widget = child.get_backend_widget()
            expand = 1 if child.stretchable(YUIDimension.YD_VERT) else 0

            # If the child requests horizontal stretch, set its QSizePolicy to Expanding
            try:
                if expand == 1:
                    sp = widget.sizePolicy()
                    try:
                        sp.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Expanding)
                    except Exception:
                        try:
                            sp.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
                        except Exception:
                            pass
                    widget.setSizePolicy(sp)
            except Exception:
                pass

            self._backend_widget.setEnabled(bool(self._enabled))
            try:
                self._logger.debug("YVBoxQt: adding child %s expand=%s", child.widgetClass(), expand)
            except Exception:
                pass
            layout.addWidget(widget, stretch=expand)
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def _set_backend_enabled(self, enabled):
        """Enable/disable the VBox container and propagate to children."""
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception:
                    pass
        except Exception:
            pass
        try:
            for c in list(getattr(self, "_children", []) or []):
                try:
                    c.setEnabled(enabled)
                except Exception:
                    pass
        except Exception:
            pass
