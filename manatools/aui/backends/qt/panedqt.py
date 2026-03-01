# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains all Qt backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''

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
        """Create the underlying QSplitter and apply weight-based stretch factors.

        ``QSplitter.setStretchFactor(index, factor)`` is Qt's native mechanism for
        proportional pane sizing – it maps directly to YWidget ``weight(axis)``.
        Weights are read from the children's ``weight(YD_VERT)`` (vertical splitter)
        or ``weight(YD_HORIZ)`` (horizontal splitter).  A weight of 0 means the pane
        keeps a fixed size determined by its minimum size hint.

        Example mapping from dnfdragora:
        - vertical paned: hbox_middle.weight(YD_VERT)=67, info.weight(YD_VERT)=33  →
          setStretchFactor(0, 67), setStretchFactor(1, 33)  → 2/3-1/3 vertical split.
        """
        if QSplitter is None or Qt is None:
            raise RuntimeError("Qt6 is not available")
        orient = Qt.Horizontal if self._orientation == YUIDimension.YD_HORIZ else Qt.Vertical
        self._backend_widget = QSplitter(orient)
        self._logger.debug("Created QSplitter orientation=%s", "H" if orient == Qt.Horizontal else "V")

        axis = YUIDimension.YD_HORIZ if self._orientation == YUIDimension.YD_HORIZ else YUIDimension.YD_VERT

        for idx, child in enumerate(self._children):
            widget = child.get_backend_widget()
            if widget is not None:
                self._backend_widget.addWidget(widget)
                try:
                    w = int(child.weight(axis) or 0)
                    self._backend_widget.setStretchFactor(idx, w)
                    self._logger.debug(
                        "QSplitter child[%d] %s: weight=%d",
                        idx, getattr(child, "debugLabel", lambda: repr(child))(), w,
                    )
                except Exception:
                    self._logger.exception("QSplitter setStretchFactor[%d] failed", idx)
                self._logger.debug("Added existing child %d to splitter during creation", idx)

        self._apply_sizes_from_weights()

    def _apply_sizes_from_weights(self):
        """Set QSplitter initial sizes from child weights.

        ``setStretchFactor`` controls how extra space is distributed after the
        initial render, but does not set the absolute initial sizes.  To get the
        intended ratio at startup (e.g. 67:33) we compute pixel sizes from the
        total splitter size and call ``setSizes()``.  This is deferred to the
        first show event so that the splitter has an allocated size.

        If no child has a declared weight the call is skipped.
        """
        if self._backend_widget is None or QSplitter is None:
            return

        children = list(getattr(self, "_children", []))
        if len(children) < 2:
            return

        axis = YUIDimension.YD_HORIZ if self._orientation == YUIDimension.YD_HORIZ else YUIDimension.YD_VERT

        try:
            weights = []
            for c in children:
                try:
                    w = int(c.weight(axis) or 0)
                except Exception:
                    w = 0
                weights.append(w)

            total_w = sum(weights)
            if total_w <= 0:
                self._logger.debug("YPanedQt _apply_sizes_from_weights: no weights – skipping")
                return

            # Apply stretch factors (controls distribution of surplus space).
            for idx, w in enumerate(weights):
                try:
                    self._backend_widget.setStretchFactor(idx, w)
                except Exception:
                    self._logger.exception("setStretchFactor(%d, %d) failed", idx, w)

            self._logger.debug(
                "YPanedQt _apply_sizes_from_weights: weights=%s total=%d", weights, total_w
            )

            # Compute initial pixel sizes once the splitter has a real size.
            def _set_initial_sizes():
                try:
                    if self._orientation == YUIDimension.YD_HORIZ:
                        total_px = self._backend_widget.width()
                    else:
                        total_px = self._backend_widget.height()
                    if not total_px or total_px <= 0:
                        return  # not realized yet; stretch factors will handle later

                    sizes = [int(total_px * w / total_w) for w in weights]
                    # Correct rounding drift on the last element.
                    sizes[-1] = max(0, total_px - sum(sizes[:-1]))
                    self._backend_widget.setSizes(sizes)
                    self._logger.debug(
                        "YPanedQt _set_initial_sizes: total_px=%d weights=%s sizes=%s",
                        total_px, weights, sizes,
                    )
                except Exception:
                    self._logger.exception("YPanedQt _set_initial_sizes failed")

            try:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, _set_initial_sizes)
            except Exception:
                self._logger.exception("QTimer.singleShot failed; applying sizes immediately")
                try:
                    _set_initial_sizes()
                except Exception:
                    pass
        except Exception:
            self._logger.exception("YPanedQt _apply_sizes_from_weights: unexpected failure")

    def addChild(self, child):
        """Add a child to the splitter, limited to two children.

        Calls the base class ``addChild`` (which appends to ``_children``) and
        then attaches the child's backend widget to the QSplitter.  Stretch
        factors are reapplied when the second child arrives so the initial
        size ratio is honoured.
        """
        # Guard BEFORE calling super() so we can check current child count.
        current_count = len(getattr(self, "_children", []))
        if current_count >= 2:
            self._logger.warning("YPanedQt can only manage two children; ignoring extra child")
            return

        super().addChild(child)

        if getattr(self, "_backend_widget", None) is None:
            return

        try:
            widget = child.get_backend_widget() if hasattr(child, "get_backend_widget") else getattr(child, "_backend_widget", None)
            if widget is not None:
                self._backend_widget.addWidget(widget)
            self._logger.debug(
                "Added child to splitter: %s",
                getattr(child, "debugLabel", lambda: repr(child))(),
            )
            # When the second child is attached, apply weight-based sizing.
            if len(self._children) == 2:
                self._apply_sizes_from_weights()
        except Exception as e:
            self._logger.error("addChild error: %s", e, exc_info=True)
