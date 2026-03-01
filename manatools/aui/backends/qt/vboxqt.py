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
        """Create the Qt VBox backend widget and configure per-child stretch factors.

        Uses ``QLayout.SetDefaultConstraint`` instead of ``SetMinimumSize`` so that
        parent containers (e.g. a QSplitter / YPanedQt) can freely resize this widget
        below its minimum size hint, enabling proportional weight splits.
        The native Qt ``stretch`` parameter in ``addWidget`` translates YWidget weights
        directly into QBoxLayout proportional space allocation.
        """
        self._backend_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self._backend_widget)
        layout.setContentsMargins(1, 1, 1, 1)
        # SetDefaultConstraint (the Qt default) does NOT pin the widget minimum to
        # minimumSizeHint(), allowing parent containers to allocate less space when
        # proportional weights demand it.  SetMinimumSize was preventing the 2/3-1/3
        # split because the tree/table VBox had a large minimumSizeHint.
        layout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        
        # Map YWidget weights and stretchable flags to Qt layout stretch factors.
        # Weight semantics: if any child has a positive weight (>0) use those
        # weights as stretch factors; otherwise give equal stretch (1) to
        # children that are marked stretchable. Non-stretchable children get 0.
        try:
            child_weights = [int(child.weight(YUIDimension.YD_VERT) or 0) for child in self._children]
        except Exception:
            child_weights = [0 for _ in self._children]
        has_positive = any(w > 0 for w in child_weights)

        for idx, child in enumerate(self._children):
            widget = child.get_backend_widget()
            weight = int(child_weights[idx]) if idx < len(child_weights) else 0
            if has_positive:
                stretch = weight
            else:
                stretch = 1 if child.stretchable(YUIDimension.YD_VERT) else 0

            # If the child will receive extra space, set its QSizePolicy to Expanding
            try:
                if stretch > 0:
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
                self._logger.debug("YVBoxQt: adding child %s stretch=%s weight=%s", child.widgetClass(), stretch, weight)
            except Exception:
                pass
            layout.addWidget(widget, stretch=stretch)
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

    def addChild(self, child):
        """Attach child's backend widget to this VBox when added at runtime."""
        super().addChild(child)
        try:
            if getattr(self, "_backend_widget", None) is None:
                return

            def _deferred_attach():
                try:
                    widget = child.get_backend_widget()
                    try:
                        weight = int(child.weight(YUIDimension.YD_VERT) or 0)
                    except Exception:
                        weight = 0
                    # If dynamic addition, use explicit weight when >0, otherwise
                    # fall back to stretchable flag (equal-share represented by 1).
                    stretch = weight if weight > 0 else (1 if child.stretchable(YUIDimension.YD_VERT) else 0)
                    try:
                        if stretch > 0:
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
                    try:
                        lay = self._backend_widget.layout()
                        if lay is None:
                            lay = QtWidgets.QVBoxLayout(self._backend_widget)
                            self._backend_widget.setLayout(lay)
                        lay.addWidget(widget, stretch=stretch)
                        try:
                            widget.show()
                        except Exception:
                            pass
                        try:
                            widget.updateGeometry()
                        except Exception:
                            pass
                    except Exception:
                        try:
                            self._logger.exception("YVBoxQt.addChild: failed to attach child")
                        except Exception:
                            pass
                except Exception:
                    pass

            # Defer attach to next event loop iteration so child's __init__ can complete
            try:
                QtCore.QTimer.singleShot(0, _deferred_attach)
            except Exception:
                # fallback: attach immediately
                _deferred_attach()
        except Exception:
            pass
