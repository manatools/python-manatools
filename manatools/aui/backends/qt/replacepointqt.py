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

class YReplacePointQt(YSingleChildContainerWidget):
    """
    Qt backend implementation of YReplacePoint.

    A placeholder container that hosts exactly one child. The child can be
    removed and replaced at runtime, and showChild() should be called after
    creating/adding a new child to attach and present it in the backend view.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._backend_widget = None
        self._layout = None
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        try:
            self._logger.debug("%s.__init__", self.__class__.__name__)
        except Exception:
            pass

    def widgetClass(self):
        return "YReplacePoint"

    def _create_backend_widget(self):
        """Create a QWidget container with a vertical layout to host the single child."""
        try:
            container = QtWidgets.QWidget()
            # Use a QStackedLayout so the single active child is shown reliably
            layout = QtWidgets.QStackedLayout()
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(5)
            container.setLayout(layout)
            self._backend_widget = container
            self._layout = layout
            # Default to expanding so parents like YFrame can allocate space
            try:
                sp = container.sizePolicy()
                try:
                    sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Expanding)
                    sp.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Expanding)
                except Exception:
                    try:
                        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
                        sp.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
                    except Exception:
                        pass
                container.setSizePolicy(sp)
            except Exception:
                pass
            self._backend_widget.setEnabled(bool(self._enabled))
            # If a child already exists, attach it now
            try:
                if self.child():
                    cw = self.child().get_backend_widget()
                    self._logger.debug("Attaching existing child %s", self.child().widgetClass())
                    if cw:
                        try:
                            cw.setParent(self._backend_widget)
                        except Exception:
                            pass
                        try:
                            self._layout.addWidget(cw)
                            try:
                                self._layout.setCurrentWidget(cw)
                            except Exception:
                                pass
                        except Exception:
                            try:
                                self._layout.addWidget(cw)
                            except Exception:
                                pass
                else:
                    self._logger.debug("No existing child to attach")
            except Exception as e:
                try:
                    self._logger.error("_create_backend_widget attach child error: %s", e, exc_info=True)
                except Exception:
                    pass
            try:
                self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
            except Exception:
                pass
        except Exception as e:
            try:
                self._logger.error("_create_backend_widget error: %s", e, exc_info=True)
            except Exception:
                pass
            self._backend_widget = None
            self._layout = None

    def _set_backend_enabled(self, enabled):
        """Enable/disable the container and propagate to its logical child."""
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.setEnabled(bool(enabled))
        except Exception:
            pass
        try:
            ch = self.child()
            if ch is not None:
                ch.setEnabled(enabled)
        except Exception:
            pass

    def stretchable(self, dim: YUIDimension):
        """Propagate stretchability from the single child to the container."""
        try:
            ch = self.child()
            if ch is None:
                return False
            try:
                if bool(ch.stretchable(dim)):
                    return True
            except Exception:
                pass
            try:
                if bool(ch.weight(dim)):
                    return True
            except Exception:
                pass
        except Exception:
            pass
        return False

    def _attach_child_backend(self):
        """Attach the current child's backend into this container layout (no redraw)."""
        # Ensure the backend container exists
        if not (self._backend_widget and self._layout and self.child()):
            self._logger.debug("_attach_child_backend called but no backend or no child to attach")
            return
        try:
            if self._layout.count() > 0:
                self._logger.warning("_attach_child_backend: layout is not empty")
            # Clear previous layout widgets 
            try:
                while self._layout.count():
                    it = self._layout.takeAt(0)
                    w = it.widget() if it else None
                    if w:
                        w.setParent(None)
            except Exception:
                pass
            # Ensure ReplacePoint expands to show content even if child isn't stretchable
            try:
                sp = self._backend_widget.sizePolicy()
                try:
                    sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Expanding)
                    sp.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Expanding)
                except Exception:
                    try:
                        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
                        sp.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
                    except Exception:
                        pass
                self._backend_widget.setSizePolicy(sp)
            except Exception:
                self._logger.exception("_attach_child_backend: sizePolicy failed")
                pass
            ch = self.child()
            cw = ch.get_backend_widget()
            if cw:
                try:
                    self._logger.debug("_attach_child_backend: layout.count before add = %s", self._layout.count())
                except Exception:
                    pass
                try:
                    # Debug info to help diagnose invisible children
                    try:
                        self._logger.debug("_attach_child_backend: attaching widget type=%s parent=%s visible=%s sizeHint=%s",
                                           type(cw), getattr(cw, 'parent', lambda: None)(), getattr(cw, 'isVisible', lambda: False)(), getattr(cw, 'sizeHint', lambda: None)())
                    except Exception:
                        pass
                except Exception:
                    pass
                try:
                    # Ensure the widget is parented to our container before adding
                    try:
                        cw.setParent(self._backend_widget)
                    except Exception:
                        pass
                    self._layout.addWidget(cw)
                    try:
                        # If using QStackedLayout, show the new widget as current
                        try:
                            self._layout.setCurrentWidget(cw)
                        except Exception:
                            try:
                                # fallback to setCurrentIndex if available
                                idx = self._layout.indexOf(cw)
                                if idx is not None and idx >= 0:
                                    try:
                                        self._layout.setCurrentIndex(idx)
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    # fallback: try remove any previous parent then add
                    try:
                        try:
                            cw.setParent(None)
                        except Exception:
                            pass
                        self._layout.addWidget(cw)
                    except Exception:
                        self._logger.exception("_attach_child_backend: addWidget fallback failed")
                # Encourage the child to expand so content becomes visible
                # Encourage the child to expand so content becomes visible
                try:
                    sp_cw = cw.sizePolicy()
                    try:
                        sp_cw.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Expanding)
                        sp_cw.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Expanding)
                    except Exception:
                        try:
                            sp_cw.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
                            sp_cw.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
                        except Exception:
                            pass
                    cw.setSizePolicy(sp_cw)
                except Exception:
                    pass
                try:
                    # Ensure the single child gets stretch in the layout (stacked ignores stretch but keep for safety)
                    try:
                        self._layout.setStretch(0, 1)
                    except Exception:
                        pass
                    try:
                        self._logger.debug("_attach_child_backend: layout.count after add = %s currentWidget=%s", self._layout.count(), getattr(self._layout, 'currentWidget', lambda: None)())
                    except Exception:
                        pass
                except Exception:
                    pass
                try:
                    cw.show()
                    try:
                        cw.raise_()
                    except Exception:
                        pass
                    try:
                        cw.updateGeometry()
                    except Exception:
                        pass
                    # If sizeHint is empty, give a small visible minimum so layout doesn't collapse
                    try:
                        sh = cw.sizeHint()
                        if sh is not None and (sh.width() == 0 or sh.height() == 0):
                            try:
                                mh = max(24, sh.height()) if hasattr(sh, 'height') else 24
                                mw = max(24, sh.width()) if hasattr(sh, 'width') else 24
                                cw.setMinimumSize(mw, mh)
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            self._logger.exception("_attach_child_backend failed")
            pass

    def addChild(self, child):
        """Add logical child and attach backend if possible (no forced redraw)."""
        super().addChild(child)
        self._logger.debug("addChild: %s", child.debugLabel())
        self._attach_child_backend()

    def showChild(self):
        """
        Attach and show the newly added child in the backend view.
        This removes any previous widget from the layout and inserts
        the current child's backend widget.
        """
        if not (self._backend_widget and self._layout and self.child()):
            self._logger.debug("showChild called but no backend or no child to attach")
            return        
        try:
            # Reuse the attach helper
            # Force a dialog layout recalculation and redraw, similar to libyui's recalcLayout.
            try:
                dlg = self.findDialog()
                if dlg is not None:
                    qwin = getattr(dlg, "_qwidget", None)
                    if qwin:
                        # Trigger local layout updates first
                        try:
                            if self._layout is not None:
                                self._layout.invalidate()
                                try:
                                    self._layout.activate()
                                except Exception:
                                    pass
                            if self._backend_widget is not None:
                                self._backend_widget.updateGeometry()
                                self._backend_widget.setVisible(True)
                                self._backend_widget.update()
                        except Exception:
                            pass
                        try:
                            qwin.update()
                            try:
                                ch = self.child()
                                if ch is not None:
                                    cw = ch.get_backend_widget()
                                    if cw:
                                        cw.show()
                            except Exception:
                                pass
                            
                            #qwin.repaint()
                        except Exception:
                            self._logger.exception("showChild: repaint failed")
                            pass
                        # Activate the dialog's layout if present
                        try:
                            lay = qwin.layout()
                            if lay is not None:
                                try:
                                    lay.invalidate()
                                except Exception:
                                    pass
                                try:
                                    lay.activate()
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        # Grow the window to accommodate any wider content, but
                        # NEVER shrink: adjustSize() would shrink the window when
                        # switching to lighter content, compressing sibling columns
                        # (e.g. the tree column squeezed by long checkbox labels on
                        # the other side of the HBox).
                        try:
                            hint = qwin.sizeHint()
                            cur_w = qwin.width()
                            cur_h = qwin.height()
                            if hint is not None and hint.isValid():
                                new_w = max(cur_w, hint.width())
                                new_h = max(cur_h, hint.height())
                                if new_w != cur_w or new_h != cur_h:
                                    qwin.resize(new_w, new_h)
                        except Exception:
                            self._logger.exception("showChild: grow-resize failed")
                            pass
                        try:
                            app = QtWidgets.QApplication.instance()
                            if app:
                                try:
                                    app.processEvents(QtCore.QEventLoop.AllEvents)
                                except Exception:
                                    app.processEvents()
                        except Exception:
                            self._logger.exception("showChild: processEvents failed")
                            pass
                    else:
                        self._logger.debug("showChild: dialog has no _qwidget")
            except Exception:
                pass
        except Exception as e:
            try:
                self._logger.error("showChild error: %s", e, exc_info=True)
            except Exception:
                pass

    def deleteChildren(self):
        """
        Remove the logical child and clear the backend layout so new children
        can be added and shown afterwards.
        """
        try:
            # Clear backend layout
            if self._layout is not None:
                try:
                    # Properly remove and hide widgets so layout recalculates
                    while self._layout.count():
                        it = self._layout.takeAt(0)
                        w = it.widget() if it else None
                        if w:
                            try:
                                try:
                                    self._layout.removeWidget(w)
                                except Exception:
                                    pass
                                try:
                                    w.hide()
                                except Exception:
                                    pass
                                try:
                                    w.setParent(None)
                                except Exception:
                                    pass
                                try:
                                    w.update()
                                except Exception:
                                    pass
                            except Exception:
                                pass
                except Exception:
                    pass
            # Clear model children
            super().deleteChildren()
        except Exception as e:
            try:
                self._logger.error("deleteChildren error: %s", e, exc_info=True)
            except Exception:
                pass
