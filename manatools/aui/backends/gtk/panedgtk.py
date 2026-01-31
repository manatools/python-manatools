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

    - Paned is stretchable by default on both directions.
    - Children are set to expand and fill, similar to HBox/VBox behavior.
    """

    def __init__(self, parent=None, dimension: YUIDimension = YUIDimension.YD_HORIZ):
        super().__init__(parent)
        self._logger = logging.getLogger("manatools.aui.gtk.YPanedGtk")
        self._orientation = dimension
        self._backend_widget = None
        # Make paned stretchable by default so it fills available space
        try:
            self.setStretchable(YUIDimension.YD_HORIZ, True)
            self.setStretchable(YUIDimension.YD_VERT, True)
        except Exception:
            self._logger.debug("Default stretchable setup failed", exc_info=True)

    def widgetClass(self):
        return "YPaned"

    # --- size policy helpers ---
    def setStretchable(self, dimension, stretchable):
        """Override stretchable to re-apply size policy using base attributes."""
        try:
            super().setStretchable(dimension, stretchable)
        except Exception:
            self._logger.exception("setStretchable: base implementation failed")
        self._apply_size_policy()

    def _apply_size_policy(self):
        """
        Apply GTK4 expand/alignment to the paned and its children using YUI stretch/weights.
        Ensures the paned and children fill the allocated space.
        """
        if self._backend_widget is None or Gtk is None:
            return
        try:
            # Read stretch flags from base YWidget
            h_stretch = bool(self.stretchable(YUIDimension.YD_HORIZ))
            v_stretch = bool(self.stretchable(YUIDimension.YD_VERT))
            # Read weights from base YWidget; default to 0.0 if not provided
            try:
                w_h = float(self.weight(YUIDimension.YD_HORIZ))
            except Exception:
                w_h = 0.0
            try:
                w_v = float(self.weight(YUIDimension.YD_VERT))
            except Exception:
                w_v = 0.0

            eff_h = bool(h_stretch or (w_h > 0.0))
            eff_v = bool(v_stretch or (w_v > 0.0))

            # Paned should expand and fill
            try:
                self._backend_widget.set_hexpand(eff_h)
            except Exception:
                self._logger.debug("set_hexpand failed on paned", exc_info=True)
            try:
                self._backend_widget.set_vexpand(eff_v)
            except Exception:
                self._logger.debug("set_vexpand failed on paned", exc_info=True)
            try:
                self._backend_widget.set_halign(Gtk.Align.FILL if eff_h else Gtk.Align.START)
            except Exception:
                self._logger.debug("set_halign failed on paned", exc_info=True)
            try:
                self._backend_widget.set_valign(Gtk.Align.FILL if eff_v else Gtk.Align.START)
            except Exception:
                self._logger.debug("set_valign failed on paned", exc_info=True)

            # Ensure children fill their panes (like HBox/VBox)
            for ch in getattr(self, "_children", []):
                try:
                    bw = ch.get_backend_widget() if hasattr(ch, "get_backend_widget") else getattr(ch, "_backend_widget", None)
                    if bw is None:
                        continue
                    bw.set_hexpand(True)
                    bw.set_vexpand(True)
                    bw.set_halign(Gtk.Align.FILL)
                    bw.set_valign(Gtk.Align.FILL)
                except Exception:
                    self._logger.debug("Failed to apply child size policy for %s", getattr(ch, "debugLabel", lambda: repr(ch))(), exc_info=True)

            self._logger.debug(
                "_apply_size_policy: h_stretch=%s v_stretch=%s w_h=%s w_v=%s eff_h=%s eff_v=%s",
                h_stretch, v_stretch, w_h, w_v, eff_h, eff_v
            )
        except Exception:
            self._logger.exception("_apply_size_policy: unexpected failure")

    def _apply_child_props(self, child_widget):
        """
        Ensure a child widget expands and fills its allocated pane area.
        """
        if child_widget is None or Gtk is None:
            return
        try:
            child_widget.set_hexpand(True)
        except Exception:
            self._logger.debug("child.set_hexpand failed", exc_info=True)
        try:
            child_widget.set_vexpand(True)
        except Exception:
            self._logger.debug("child.set_vexpand failed", exc_info=True)
        try:
            child_widget.set_halign(Gtk.Align.FILL)
        except Exception:
            self._logger.debug("child.set_halign failed", exc_info=True)
        try:
            child_widget.set_valign(Gtk.Align.FILL)
        except Exception:
            self._logger.debug("child.set_valign failed", exc_info=True)

    def _create_backend_widget(self):
        """
        Create the underlying Gtk.Paned with the chosen orientation and attach existing children.
        """
        if Gtk is None:
            raise RuntimeError("GTK4 is not available")
        orient = Gtk.Orientation.HORIZONTAL if self._orientation == YUIDimension.YD_HORIZ else Gtk.Orientation.VERTICAL
        self._backend_widget = Gtk.Paned.new(orient)
        self._logger.debug("Created Gtk.Paned orientation=%s", "H" if orient == Gtk.Orientation.HORIZONTAL else "V")

        # Paned should fill available space
        try:
            self._backend_widget.set_hexpand(True)
            self._backend_widget.set_vexpand(True)
            self._backend_widget.set_halign(Gtk.Align.FILL)
            self._backend_widget.set_valign(Gtk.Align.FILL)
            # Avoid shrinking children below their minimum size
            if hasattr(self._backend_widget, "set_shrink_start_child"):
                self._backend_widget.set_shrink_start_child(False)
            if hasattr(self._backend_widget, "set_shrink_end_child"):
                self._backend_widget.set_shrink_end_child(False)
        except Exception:
            self._logger.debug("Initial paned size setup failed", exc_info=True)

        # Attach already collected children (like HBox/VBox does)
        for idx, child in enumerate(getattr(self, "_children", [])):
            try:
                widget = child.get_backend_widget() if hasattr(child, "get_backend_widget") else getattr(child, "_backend_widget", None)
                if widget is None:
                    self._logger.debug("Child %s has no backend widget yet", getattr(child, "debugLabel", lambda: repr(child))())
                    continue
                if idx == 0:
                    self._backend_widget.set_start_child(widget)
                    self._logger.debug("Set start child: %s", child.debugLabel())
                elif idx == 1:
                    self._backend_widget.set_end_child(widget)
                    self._logger.debug("Set end child: %s", child.debugLabel())
                else:
                    self._logger.warning("YPanedGtk can only manage two children; ignoring extra child")
                # Ensure child fills
                self._apply_child_props(widget)
            except Exception as e:
                self._logger.error("Attaching child[%d] failed: %s", idx, e, exc_info=True)

        # Apply size policy once backend is ready
        self._apply_size_policy()

    def addChild(self, child: YWidget):
        """
        Add a child to the paned: first goes to 'start', second to 'end'.
        Children are set to expand and fill.
        """
        if len(self._children) == 2:
            self._logger.warning("YPanedGtk can only manage two children; ignoring extra child")
            return
        super().addChild(child)
        if self._backend_widget is None:
            return
        try:
            widget = child.get_backend_widget() if hasattr(child, "get_backend_widget") else getattr(child, "_backend_widget", None)
            if child == self._children[0]:
                if widget is not None:
                    self._backend_widget.set_start_child(widget)
                    self._apply_child_props(widget)
                self._logger.debug("Set start child: %s", getattr(child, "debugLabel", lambda: repr(child))())
            elif len(self._children) > 1 and child == self._children[1]:
                if widget is not None:
                    self._backend_widget.set_end_child(widget)
                    self._apply_child_props(widget)
                self._logger.debug("Set end child: %s", getattr(child, "debugLabel", lambda: repr(child))())
            else:
                self._logger.warning("YPanedGtk can only manage two children; ignoring extra child")
        except Exception as e:
            self._logger.error("addChild error: %s", e, exc_info=True)
        # Re-apply overall size policy
        self._apply_size_policy()
