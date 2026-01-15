"""
Qt backend implementation for YUI
"""

from PySide6 import QtWidgets
import logging
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
        self._logger = logging.getLogger(
            f"manatools.aui.qt.{self.__class__.__name__}"
        )

    def widgetClass(self):
        return "YFrame"

    def stretchable(self, dim: YUIDimension):
        """Return True if the frame should stretch in given dimension."""
        try:
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
                    # QGroupBox uses setTitle
                    if hasattr(self._backend_widget, "setTitle"):
                        self._backend_widget.setTitle(self._label)
                except Exception:
                    pass
        except Exception:
            pass

    def _apply_child_policy_and_stretch(self, child_widget):
        """Compute child's stretch and apply Qt size policy and return stretch."""
        stretch = 0
        try:
            try:
                weight = int(self.child().weight(YUIDimension.YD_VERT))
            except Exception:
                weight = 0
            try:
                stretchable_vert = bool(self.child().stretchable(YUIDimension.YD_VERT))
            except Exception:
                stretchable_vert = False
            stretch = weight if weight > 0 else (1 if stretchable_vert else 0)
        except Exception:
            stretch = 0

        # set child's QSizePolicy based on logical flags
        try:
            sp = child_widget.sizePolicy()
            try:
                horiz_expand = (
                    QtWidgets.QSizePolicy.Expanding
                    if bool(self.child().stretchable(YUIDimension.YD_HORIZ))
                    else QtWidgets.QSizePolicy.Fixed
                )
            except Exception:
                horiz_expand = QtWidgets.QSizePolicy.Fixed
            try:
                vert_expand = (
                    QtWidgets.QSizePolicy.Expanding if stretch > 0 else QtWidgets.QSizePolicy.Preferred
                )
            except Exception:
                vert_expand = QtWidgets.QSizePolicy.Fixed
            sp.setHorizontalPolicy(horiz_expand)
            sp.setVerticalPolicy(vert_expand)
            child_widget.setSizePolicy(sp)
        except Exception:
            pass

        return stretch

    def _attach_child_backend(self):
        """Attach existing child backend widget to the groupbox layout."""
        if not (self._backend_widget and self._group_layout and self.child()):
            return
        try:
            w = self.child().get_backend_widget()
            if not w:
                return

            # clear existing widgets
            try:
                while self._group_layout.count():
                    it = self._group_layout.takeAt(0)
                    if it and it.widget():
                        it.widget().setParent(None)
            except Exception:
                pass

            # compute stretch and apply policy
            stretch = self._apply_child_policy_and_stretch(w)

            # set group size policy to reflect child's desire for expansion
            try:
                sp_grp = self._backend_widget.sizePolicy()
                grp_vert_expand = (
                    QtWidgets.QSizePolicy.Expanding if stretch > 0 else QtWidgets.QSizePolicy.Preferred
                )
                sp_grp.setVerticalPolicy(grp_vert_expand)
                sp_grp.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
                self._backend_widget.setSizePolicy(sp_grp)
            except Exception:
                pass

            # add widget with stretch factor (if supported)
            try:
                self._group_layout.addWidget(w, stretch)
            except Exception:
                try:
                    self._group_layout.addWidget(w)
                except Exception:
                    pass
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
            # Ensure the group's widget minimum size follows the layout's minimumSizeHint.
            # This prevents Qt from compressing the groupbox contents to zero when nested
            # inside other layouts. We keep this local to frame/groupbox layouts.
            try:
                layout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
            except Exception:
                pass
            layout.setContentsMargins(6, 6, 6, 6)
            layout.setSpacing(4)
            self._backend_widget = grp
            self._group_layout = layout
            self._backend_widget.setEnabled(bool(self._enabled))

            # set group's size policy according to logical stretch of this frame
            try:
                frame_stretchable = bool(self.stretchable(YUIDimension.YD_VERT))
            except Exception:
                frame_stretchable = False
            try:
                sp_grp = self._backend_widget.sizePolicy()
                sp_grp.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
                sp_grp.setVerticalPolicy(
                    QtWidgets.QSizePolicy.Expanding if frame_stretchable else QtWidgets.QSizePolicy.Preferred
                )
                self._backend_widget.setSizePolicy(sp_grp)
            except Exception:
                pass

            # attach child if present (apply same policy/stretches)
            if self.child():
                try:
                    w = self.child().get_backend_widget()
                    if w:
                        stretch = self._apply_child_policy_and_stretch(w)
                        try:
                            layout.addWidget(w, stretch)
                        except Exception:
                            try:
                                layout.addWidget(w)
                            except Exception:
                                pass
                except Exception:
                    pass
            try:
                self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
            except Exception:
                pass
            return
        except Exception:
            # fallback to a plain QWidget container
            try:
                container = QtWidgets.QWidget()
                layout = QtWidgets.QVBoxLayout(container)
                # Keep fallback container constrained as well (same rationale).
                try:
                    layout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
                except Exception:
                    pass
                layout.setContentsMargins(6, 6, 6, 6)
                layout.setSpacing(4)
                self._backend_widget = container
                self._group_layout = layout
                if self.child():
                    try:
                        w = self.child().get_backend_widget()
                        if w:
                            stretch = self._apply_child_policy_and_stretch(w)
                            try:
                                layout.addWidget(w, stretch)
                            except Exception:
                                try:
                                    layout.addWidget(w)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                try:
                    self._logger.debug("_create_backend_widget (container): <%s>", self.debugLabel())
                except Exception:
                    pass
                return
            except Exception:
                self._backend_widget = None
                self._group_layout = None
                return

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
