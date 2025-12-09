"""
Qt backend implementation for YUI
"""

from PySide6 import QtWidgets
from ...yui_common import *

class YFrameQt(YSingleChildContainerWidget):
    """
    Qt backend implementation of YFrame.
    - Uses QGroupBox to present a labeled framed container.
    - Single child is placed inside the group's layout.
    - Exposes simple property support for 'label'.
    """
    def __init__(self, parent=None, label=""):
        super().__init__(parent)
        self._label = label
        self._backend_widget = None
        self._group_layout = None

    def widgetClass(self):
        return "YFrame"

    def stretchable(self, dim: YUIDimension):
        """Return True if the frame should stretch in given dimension.
        The frame is stretchable when its child is stretchable or has a layout weight.
        """
        try:
            # prefer explicit single child
            child = self.child()
            if child is None:
                return False
            try:
                if bool(child.stretchable(dim)):
                    return True
            except Exception:
                pass
            try:
                if bool(child.weight(dim)):
                    return True
            except Exception:
                pass
        except Exception:
            pass
        return False

    def label(self):
        return self._label

    def setLabel(self, newLabel):
        """Set the frame label and update the Qt widget if created."""
        try:
            self._label = newLabel
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setTitle(self._label)
                except Exception:
                    pass
        except Exception:
            pass

    def _attach_child_backend(self):
        """Attach existing child backend widget to the groupbox layout."""
        if not (self._backend_widget and self._group_layout and self.child()):
            return
        try:
            w = self.child().get_backend_widget()
            if w:
                # clear any existing widgets in layout (defensive)
                try:
                    while self._group_layout.count():
                        it = self._group_layout.takeAt(0)
                        if it and it.widget():
                            it.widget().setParent(None)
                except Exception:
                    pass
                self._group_layout.addWidget(w)
        except Exception:
            pass

    def addChild(self, child):
        """Override to attach backend child when available."""
        super().addChild(child)
        self._attach_child_backend()

    def _create_backend_widget(self):
        """Create the QGroupBox + layout and attach child if present."""
        try:
            grp = QtWidgets.QGroupBox(self._label)
            layout = QtWidgets.QVBoxLayout(grp)
            layout.setContentsMargins(6, 6, 6, 6)
            layout.setSpacing(4)
            self._backend_widget = grp
            self._group_layout = layout

            # attach child widget if already set
            if self.child():
                try:
                    w = self.child().get_backend_widget()
                    if w:
                        layout.addWidget(w)
                except Exception:
                    pass
        except Exception:
            # fallback to a plain QWidget container if QGroupBox creation fails
            try:
                container = QtWidgets.QWidget()
                layout = QtWidgets.QVBoxLayout(container)
                layout.setContentsMargins(6, 6, 6, 6)
                layout.setSpacing(4)
                self._backend_widget = container
                self._group_layout = layout
                if self.child():
                    try:
                        w = self.child().get_backend_widget()
                        if w:
                            layout.addWidget(w)
                    except Exception:
                        pass
            except Exception:
                self._backend_widget = None
                self._group_layout = None

    def _set_backend_enabled(self, enabled):
        """Enable/disable the frame and propagate state to the child."""
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

    def setProperty(self, propertyName, val):
        """Handle simple properties; returns True if handled."""
        try:
            if propertyName == "label":
                self.setLabel(str(val))
                return True
        except Exception:
            pass
        return False

    def getProperty(self, propertyName):
        try:
            if propertyName == "label":
                return self.label()
        except Exception:
            pass
        return None

    def propertySet(self):
        """Return a minimal property set description (used by some backends)."""
        try:
            props = YPropertySet()
            try:
                props.add(YProperty("label", YPropertyType.YStringProperty))
            except Exception:
                pass
            return props
        except Exception:
            return None