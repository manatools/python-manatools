# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
"""
YPanedQt: Qt6 Paned widget wrapper.

- Wraps QSplitter with horizontal or vertical orientation.
- Children are added in order, up to two for parity with Gtk Paned.
"""

import logging
from ...yui_common import YWidget, YUIDimension

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QSplitter
except Exception as e:
    QSplitter = None
    Qt = None
    logging.getLogger("manatools.aui.qt.paned").error("Failed to import Qt6: %s", e, exc_info=True)


class YPanedQt(YWidget):
    """
    Qt6 implementation of YPaned using QSplitter.
    """

    def __init__(self, parent=None, dimension: YUIDimension = YUIDimension.YD_HORIZ):
        super().__init__(parent)
        self._logger = logging.getLogger("manatools.aui.qt.YPanedQt")
        self._orientation = dimension
        self._backend_widget = None
        self._children = []

    def widgetClass(self):
        return "YPaned"

    def _create_backend_widget(self):
        """
        Create the underlying QSplitter with the chosen orientation.
        """
        if QSplitter is None or Qt is None:
            raise RuntimeError("Qt6 is not available")
        orient = Qt.Horizontal if self._orientation == YUIDimension.YD_HORIZ else Qt.Vertical
        self._backend_widget = QSplitter(orient)
        self._logger.debug("Created QSplitter orientation=%s", "H" if orient == Qt.Horizontal else "V")
        for idx, child in enumerate(self._children):
            widget = child.get_backend_widget()
            if widget is not None:
                self._backend_widget.addWidget(widget)
                self._logger.debug("Added existing child %d to splitter during creation", idx)

    def addChild(self, child):
        """
        Add a child to the splitter, limiting to two children for consistency.
        """
        super().addChild(child)
        if getattr(self, "_backend_widget", None) is None:
            return

        try:
            if len(self._children) >= 2:
                self._logger.warning("YPanedQt can only manage two children; ignoring extra child")
                return
            if getattr(child, "_backend_widget", None) is not None:
                self._backend_widget.addWidget(child._backend_widget)
            self._children.append(child)
            self._logger.debug("Added child to splitter: %s", getattr(child, "debugLabel", lambda: repr(child))())
        except Exception as e:
            self._logger.error("addChild error: %s", e, exc_info=True)
