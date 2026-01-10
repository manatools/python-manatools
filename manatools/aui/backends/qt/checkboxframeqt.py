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

class YCheckBoxFrameQt(YSingleChildContainerWidget):
    """
    Qt backend for YCheckBoxFrame: a frame with a checkbox that can enable/disable its child.
    """
    def __init__(self, parent=None, label: str = "", checked: bool = False):
        super().__init__(parent)
        self._label = label or ""
        self._checked = bool(checked)
        self._auto_enable = True
        self._invert_auto = False
        self._backend_widget = None
        self._checkbox = None
        self._content_widget = None
        self._content_layout = None
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")

    def widgetClass(self):
        return "YCheckBoxFrame"

    def label(self):
        return self._label

    def setLabel(self, new_label):
        try:
            self._label = str(new_label)
            if getattr(self, "_checkbox", None) is not None:
                try:
                    # QGroupBox uses setTitle; keep compatibility if _checkbox is a QCheckBox
                    if hasattr(self._checkbox, "setTitle"):
                        self._checkbox.setTitle(self._label)
                    else:
                        self._checkbox.setText(self._label)
                except Exception:
                    pass
        except Exception:
            pass

    def setValue(self, isChecked: bool):
        try:
            self._checked = bool(isChecked)
            if self._checkbox is not None:
                try:
                    # QGroupBox supports setChecked when checkable
                    if hasattr(self._checkbox, "setChecked"):
                        self._checkbox.blockSignals(True)
                        self._checkbox.setChecked(self._checked)
                        self._checkbox.blockSignals(False)
                    else:
                        # fallback for plain checkbox widget
                        self._checkbox.blockSignals(True)
                        self._checkbox.setChecked(self._checked)
                        self._checkbox.blockSignals(False)
                except Exception:
                    pass
            # propagate enablement based on new value
            self.handleChildrenEnablement(self._checked)
        except Exception:
            pass

    def value(self):
        try:
            if self._checkbox is not None:
                # QGroupBox isChecked exists when checkable; otherwise fallback
                if hasattr(self._checkbox, "isChecked"):
                    return bool(self._checkbox.isChecked())
                if hasattr(self._checkbox, "isChecked"):
                    return bool(self._checkbox.isChecked())
        except Exception:
            pass
        return bool(self._checked)

    def autoEnable(self):
        return bool(self._auto_enable)

    def setAutoEnable(self, autoEnable: bool):
        try:
            self._auto_enable = bool(autoEnable)
            # re-evaluate children enablement
            self.handleChildrenEnablement(self.value())
        except Exception:
            pass

    def invertAutoEnable(self):
        return bool(self._invert_auto)

    def setInvertAutoEnable(self, invert: bool):
        try:
            self._invert_auto = bool(invert)
            self.handleChildrenEnablement(self.value())
        except Exception:
            pass

    def _create_backend_widget(self):
        """Create widget: use QGroupBox checkable (theme-aware) so the checkbox is in the title."""
        try:
            # Use QGroupBox to present a themed frame with a checkable title area.
            grp = QtWidgets.QGroupBox()
            grp.setTitle(self._label)
            grp.setCheckable(True)
            grp.setChecked(self._checked)
            layout = QtWidgets.QVBoxLayout(grp)
            layout.setContentsMargins(6, 6, 6, 6)
            layout.setSpacing(4)

            content = QtWidgets.QWidget()
            content_layout = QtWidgets.QVBoxLayout(content)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(4)
            layout.addWidget(content)

            self._backend_widget = grp
            # keep attribute name _checkbox for compatibility, but it's a QGroupBox now
            self._checkbox = grp
            self._content_widget = content
            self._content_layout = content_layout
            self._backend_widget.setEnabled(bool(self._enabled))

            # connect group toggled signal
            try:
                grp.toggled.connect(self._on_checkbox_toggled)
            except Exception:
                # older bindings or non-checkable objects may not have toggled
                pass

            # attach existing child if present
            try:
                if self.hasChildren():
                    self._attach_child_backend()
            except Exception:
                pass
        except Exception:
            self._backend_widget = None
            self._checkbox = None
            self._content_widget = None
            self._content_layout = None
        try:
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception:
            pass

    def _attach_child_backend(self):
        """Attach child's backend widget into content area."""
        if not (self._backend_widget and self._content_layout and self.child()):
            return

        # Safely clear existing content layout
        try:
            while self._content_layout.count():
                it = self._content_layout.takeAt(0)
                if it and it.widget():
                    it.widget().setParent(None)
        except Exception:
            pass

        # Try to obtain/create child's backend widget and insert it
        try:
            child = self.child()
            w = None
            try:
                w = child.get_backend_widget()
            except Exception:
                w = None

            if w is None:
                try:
                    child._create_backend_widget()
                    w = child.get_backend_widget()
                except Exception:
                    w = None

            if w is not None:
                # determine stretch factor from child's weight()/stretchable()
                try:
                    weight = int(child.weight(YUIDimension.YD_VERT))
                except Exception:
                    weight = 0
                try:
                    stretchable_vert = bool(child.stretchable(YUIDimension.YD_VERT))
                except Exception:
                    stretchable_vert = False
                stretch = weight if weight > 0 else (1 if stretchable_vert else 0)

                # set child's Qt size policy according to logical stretchable flags
                try:
                    sp = w.sizePolicy()
                    try:
                        horiz = QtWidgets.QSizePolicy.Expanding if bool(child.stretchable(YUIDimension.YD_HORIZ)) else QtWidgets.QSizePolicy.Fixed
                    except Exception:
                        horiz = QtWidgets.QSizePolicy.Fixed
                    try:
                        vert = QtWidgets.QSizePolicy.Expanding if stretch > 0 else QtWidgets.QSizePolicy.Fixed
                    except Exception:
                        vert = QtWidgets.QSizePolicy.Fixed
                    sp.setHorizontalPolicy(horiz)
                    sp.setVerticalPolicy(vert)
                    # When autoscale/height-for-width semantics are used by the child,
                    # preserve its existing height-for-width capability.
                    try:
                        if hasattr(sp, "setHeightForWidth"):
                            sp.setHeightForWidth(bool(getattr(child, "_auto_scale", False)))
                    except Exception:
                        pass
                    w.setSizePolicy(sp)
                except Exception:
                    pass

                # add widget with stretch factor if supported
                added = False
                try:
                    # Some PySide/PyQt bindings accept (widget, stretch)
                    self._content_layout.addWidget(w, stretch)
                    added = True
                except TypeError:
                    added = False
                except Exception:
                    added = False

                if not added:
                    try:
                        self._content_layout.addWidget(w)
                        added = True
                    except Exception:
                        added = False

                if not added:
                    # final fallback: parent the widget to content container
                    try:
                        w.setParent(self._content_widget)
                        added = True
                    except Exception:
                        added = False
        except Exception:
            # top-level protection; do not raise to caller
            pass

        # apply current enablement state (outside try that manipulates the layout)
        try:
            self.handleChildrenEnablement(self.value())
        except Exception:
            pass
