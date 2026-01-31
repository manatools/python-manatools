# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.gtk contains all GTK backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
'''
"""
YPanedGtk: GTK4 Paned widget wrapper.

- Wraps Gtk.Paned with horizontal or vertical orientation.
- Accepts up to two children; first child goes to "start", second to "end".
- Behavior similar to HBox/VBox but using native Gtk.Paned.
"""

import logging
from ...yui_common import YWidget, YUIDimension

try:
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk
except Exception as e:
    Gtk = None  # Allow import in non-GTK environments
    logging.getLogger("manatools.aui.gtk.paned").error("Failed to import GTK4: %s", e, exc_info=True)


class YPanedGtk(YWidget):
    """
    GTK4 implementation of YPaned using Gtk.Paned.
    """

    def __init__(self, parent=None, dimension: YUIDimension = YUIDimension.YD_HORIZ):
        super().__init__(parent)
        self._logger = logging.getLogger("manatools.aui.gtk.YPanedGtk")
        self._orientation = dimension
        self._backend_widget = None        

    def widgetClass(self):
        return "YPaned"

    def _create_backend_widget(self):
        """
        Create the underlying Gtk.Paned with the chosen orientation.
        """
        if Gtk is None:
            raise RuntimeError("GTK4 is not available")
        orient = Gtk.Orientation.HORIZONTAL if self._orientation == YUIDimension.YD_HORIZ else Gtk.Orientation.VERTICAL
        self._backend_widget = Gtk.Paned.new(orient)
        self._logger.debug("Created Gtk.Paned orientation=%s", "H" if orient == Gtk.Orientation.HORIZONTAL else "V")
         # Collect children first so we can apply weight-based heuristics
        children = list(self._children)

        for idx, child in enumerate(self._children):        
            self._logger.debug("Paned child: %s", child.debugLabel())
            widget = child.get_backend_widget()
            if idx == 0:
                if widget is not None:
                    self._backend_widget.set_start_child(widget)
                self._logger.debug("Set start child: %s", child.debugLabel())
            elif idx == 1:
                if widget is not None:
                    self._backend_widget.set_end_child(widget)
                self._logger.debug("Set end child: %s", child.debugLabel())
            else:
                self._logger.warning("YPanedGtk can only manage two children; ignoring extra child")

    def addChild(self, child: YWidget):
        """
        Add a child to the paned: first goes to 'start', second to 'end'.
        """
        if len(self._children) == 2:
            self._logger.warning("YPanedGtk can only manage two children; ignoring extra child")
            return
        super().addChild(child)
        if self._backend_widget is None:
            return
        try:
            if child == self._children[0]:
                if getattr(child, "_backend_widget", None) is not None:
                    self._backend_widget.set_start_child(child._backend_widget)
                self._logger.debug("Set start child: %s", getattr(child, "debugLabel", lambda: repr(child))())
            elif len(self._children) > 1 and child == self._children[1]:
                if getattr(child, "_backend_widget", None) is not None:
                    self._backend_widget.set_end_child(child._backend_widget)
                self._logger.debug("Set end child: %s", getattr(child, "debugLabel", lambda: repr(child))())
            else:
                self._logger.warning("YPanedGtk can only manage two children; ignoring extra child")
        except Exception as e:
            self._logger.error("addChild error: %s", e, exc_info=True)
