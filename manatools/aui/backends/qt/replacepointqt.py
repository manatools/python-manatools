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
            layout = QtWidgets.QVBoxLayout(container)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(5)
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
                        self._layout.addWidget(cw)
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
        if not (self._backend_widget and self._layout and self.child()):
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
                self._layout.addWidget(cw)                
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
            self._logger.debug("showChild: no backend/layout/child to show")
            return
        try:
            # Reuse the attach helper
            #self._attach_child_backend()
            # Force a dialog layout recalculation and redraw, similar to libyui's recalcLayout.
            try:
                dlg = self.findDialog()
                if dlg is not None:
                    qwin = getattr(dlg, "_qwidget", None)
                    if qwin:
                        try:
                            qwin.update()
                            self.child().get_backend_widget().show()
                            
                            #qwin.repaint()
                        except Exception:
                            self._logger.exception("showChild: repaint failed")
                            pass
                        try:
                            qwin.adjustSize()
                        except Exception:
                            self._logger.exception("showChild: adjustSize failed")
                            pass
                        try:
                            app = QtWidgets.QApplication.instance()
                            if app:
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
                    while self._layout.count():
                        it = self._layout.takeAt(0)
                        w = it.widget() if it else None
                        if w:
                            w.setParent(None)
                except Exception:
                    pass
            # Clear model children
            super().deleteChildren()
        except Exception as e:
            try:
                self._logger.error("deleteChildren error: %s", e, exc_info=True)
            except Exception:
                pass
