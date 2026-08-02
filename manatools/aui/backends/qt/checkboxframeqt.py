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
        """Set the checkbox state and propagate enablement to the child widgets."""
        try:
            self._checked = bool(isChecked)
            if self._checkbox is not None:
                try:
                    # Block signals to avoid re-entrant _on_checkbox_toggled while we
                    # programmatically change the state.
                    self._checkbox.blockSignals(True)
                    self._checkbox.setChecked(self._checked)
                    self._checkbox.blockSignals(False)
                except Exception as exc:
                    self._logger.debug("setValue: blockSignals/setChecked failed: %s", exc)
            # propagate enablement based on new value
            self._apply_children_enablement(self._checked)
        except Exception as exc:
            self._logger.debug("setValue failed: %s", exc)

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
        """Enable or disable automatic child-enablement when the checkbox is toggled."""
        try:
            self._auto_enable = bool(autoEnable)
            # re-evaluate children enablement
            self._apply_children_enablement(self.value())
        except Exception as exc:
            self._logger.debug("setAutoEnable failed: %s", exc)

    def invertAutoEnable(self):
        """Return True when child enablement is inverted (child enabled when frame is unchecked)."""
        return bool(self._invert_auto)

    def setInvertAutoEnable(self, invert: bool):
        """Invert the auto-enable logic: child is enabled when the checkbox is *un*checked."""
        try:
            self._invert_auto = bool(invert)
            self._apply_children_enablement(self.value())
        except Exception as exc:
            self._logger.debug("setInvertAutoEnable failed: %s", exc)

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
            if self._help_text:
                self._checkbox.setToolTip(self._help_text)

            # QGroupBox.toggled(bool) fires whenever the checkable group changes state.
            try:
                grp.toggled.connect(self._on_checkbox_toggled)
                self._logger.debug(
                    "_create_backend_widget: toggled signal connected for <%s>",
                    self._label,
                )
            except Exception as exc:
                self._logger.warning(
                    "_create_backend_widget: could not connect toggled signal: %s", exc
                )

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

    # ------------------------------------------------------------------
    # Signal handler
    # ------------------------------------------------------------------

    def _on_checkbox_toggled(self, checked: bool):
        """
        Slot connected to QGroupBox.toggled(bool).

        Updates the internal state, applies auto-enablement to the child
        widgets, and posts a YWidgetEvent to the containing dialog when
        notify() is active.
        """
        try:
            self._checked = bool(checked)
            self._logger.debug(
                "_on_checkbox_toggled: <%s> checked=%s", self._label, self._checked
            )
            if self._auto_enable:
                self._apply_children_enablement(self._checked)
            # Fire a ValueChanged event so the dialog event loop can react.
            try:
                if self.notify():
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
                        self._logger.debug(
                            "_on_checkbox_toggled: ValueChanged event posted for <%s>",
                            self._label,
                        )
                    else:
                        self._logger.debug(
                            "_on_checkbox_toggled: no dialog found for <%s>; event not posted",
                            self._label,
                        )
            except Exception as exc:
                self._logger.debug(
                    "_on_checkbox_toggled: event dispatch failed for <%s>: %s",
                    self._label,
                    exc,
                )
        except Exception as exc:
            self._logger.error("_on_checkbox_toggled: unexpected error: %s", exc)

    def showContent(self, visible: bool = True):
        """Show or hide the content area of the frame without affecting the checkbox."""
        try:
            self._show_content = bool(visible)
            if getattr(self, '_content_widget', None) is not None:
                self._content_widget.setVisible(bool(visible))
                # Ask the top-level window to resize itself to fit the updated layout.
                try:
                    top = self._content_widget.window()
                    if top is not None:
                        top.adjustSize()
                except Exception:
                    pass
        except Exception as exc:
            self._logger.debug("showContent failed: %s", exc)

    # ------------------------------------------------------------------
    # Children enablement helper
    # ------------------------------------------------------------------

    def _apply_children_enablement(self, isChecked: bool):
        """
        Enable or disable the logical child widget according to *isChecked*,
        respecting the autoEnable and invertAutoEnable settings.

        Does nothing when autoEnable is False.
        """
        try:
            if not self._auto_enable:
                return
            state = bool(isChecked)
            if self._invert_auto:
                state = not state
            child = self.child()
            if child is not None:
                try:
                    child.setEnabled(state)
                    self._logger.debug(
                        "_apply_children_enablement: child <%s> enabled=%s",
                        getattr(child, '_label', child.__class__.__name__),
                        state,
                    )
                except Exception as exc:
                    self._logger.debug(
                        "_apply_children_enablement: setEnabled on child failed: %s", exc
                    )
        except Exception as exc:
            self._logger.debug("_apply_children_enablement failed: %s", exc)

    # ------------------------------------------------------------------
    # Child management
    # ------------------------------------------------------------------

    def addChild(self, child):
        """Add a logical child and immediately attach its backend widget into the content area."""
        super().addChild(child)
        try:
            self._attach_child_backend()
        except Exception as exc:
            self._logger.debug("addChild: _attach_child_backend failed: %s", exc)

    # ------------------------------------------------------------------
    def setHelpText(self, help_text: str):
        super().setHelpText(help_text)
        try:
            if getattr(self, "_checkbox", None) is not None:
                self._checkbox.setToolTip(help_text)
        except Exception:
            self._logger.exception("setHelpText failed", exc_info=True)

    # Backend enable/disable
    # ------------------------------------------------------------------

    def _set_backend_enabled(self, enabled: bool):
        """
        Propagate the enabled/disabled state to the QGroupBox and the logical child.

        Called by the base class when YWidget.setEnabled() changes the widget state.
        """
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.setEnabled(bool(enabled))
                except Exception as exc:
                    self._logger.debug("_set_backend_enabled: setEnabled failed: %s", exc)
        except Exception as exc:
            self._logger.debug("_set_backend_enabled (outer) failed: %s", exc)
        # propagate to logical child so its own backend is also updated
        try:
            child = self.child()
            if child is not None:
                # When re-enabling the parent, restore child's own _enabled state.
                child._set_backend_enabled(bool(enabled) and child._enabled)
        except Exception as exc:
            self._logger.debug("_set_backend_enabled: child._set_backend_enabled failed: %s", exc)

    # ------------------------------------------------------------------
    # Property interface (used by generic dialog property accessors)
    # ------------------------------------------------------------------

    def setProperty(self, propertyName: str, val) -> bool:
        """Set a named property. Supported names: 'label', 'value', 'checked'."""
        try:
            if propertyName == "label":
                self.setLabel(str(val))
                return True
            if propertyName in ("value", "checked"):
                self.setValue(bool(val))
                return True
        except Exception as exc:
            self._logger.debug("setProperty(%s) failed: %s", propertyName, exc)
        return False

    def getProperty(self, propertyName: str):
        """Return the value of a named property. Supported names: 'label', 'value', 'checked'."""
        try:
            if propertyName == "label":
                return self.label()
            if propertyName in ("value", "checked"):
                return self.value()
        except Exception as exc:
            self._logger.debug("getProperty(%s) failed: %s", propertyName, exc)
        return None

    def propertySet(self):
        """Return the set of properties supported by this widget."""
        try:
            props = YPropertySet()
            try:
                props.add(YProperty("label", YPropertyType.YStringProperty))
                props.add(YProperty("value", YPropertyType.YBoolProperty))
            except Exception as exc:
                self._logger.debug("propertySet: could not add properties: %s", exc)
            return props
        except Exception as exc:
            self._logger.debug("propertySet failed: %s", exc)
        return None

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
            self._apply_children_enablement(self.value())
        except Exception as exc:
            self._logger.debug("_attach_child_backend: _apply_children_enablement failed: %s", exc)
