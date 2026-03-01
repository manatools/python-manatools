# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.gtk contains all GTK backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
'''
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
import logging
from ...yui_common import *

class YReplacePointGtk(YSingleChildContainerWidget):
    """
    GTK backend implementation of YReplacePoint.

    A single-child placeholder container; call showChild() after adding a new
    child to attach its backend widget inside a Gtk.Box container. deleteChildren()
    clears both the logical model and the Gtk content.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._backend_widget = None
        self._content = None
        # counter to generate stable unique page names for Gtk.Stack
        self._stack_page_counter = 0
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        try:
            self._logger.debug("%s.__init__", self.__class__.__name__)
        except Exception:
            pass

    def widgetClass(self):
        return "YReplacePoint"

    def _create_backend_widget(self):
        """Create a container that hosts a Gtk.Stack so only the active child is visible.

        Using a Gtk.Stack mirrors the Qt stacked layout approach and makes
        showing/hiding the single child more reliable across backends.
        """
        try:
            outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            outer.set_hexpand(True)
            outer.set_vexpand(True)
            try:
                outer.set_halign(Gtk.Align.FILL)
                outer.set_valign(Gtk.Align.FILL)
            except Exception:
                pass
            # Try to give a reasonable default minimum size so the area is visible
            try:
                # GTK3/4 compatibility: set_size_request may exist
                outer.set_size_request(200, 140)
            except Exception:
                try:
                    # Fallback: set a minimum content height if available
                    outer.set_minimum_size = getattr(outer, 'set_minimum_size', None)
                    if callable(outer.set_minimum_size):
                        try:
                            outer.set_minimum_size(200, 140)
                        except Exception:
                            pass
                except Exception:
                    pass
            stack = Gtk.Stack()
            try:
                stack.set_hexpand(True)
                stack.set_vexpand(True)
                try:
                    stack.set_halign(Gtk.Align.FILL)
                    stack.set_valign(Gtk.Align.FILL)
                except Exception:
                    pass
                try:
                    stack.set_size_request(200, 140)
                except Exception:
                    pass
            except Exception:
                pass
            outer.append(stack)
            self._backend_widget = outer
            self._content = stack
            # Attach child if already present
            try:
                ch = self.child()
                if ch is not None:
                    cw = ch.get_backend_widget()
                    if cw:
                        try:
                            # add_titled requires a name; use debugLabel to produce a unique id
                            name = f"child_{id(cw)}"
                            stack.add_titled(cw, name, name)
                            try:
                                stack.set_visible_child(cw)
                            except Exception:
                                pass
                        except Exception:
                            try:
                                stack.add(cw)
                            except Exception:
                                pass
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
            self._content = None

    def _set_backend_enabled(self, enabled):
        try:
            if self._backend_widget is not None:
                self._backend_widget.set_sensitive(bool(enabled))
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

    def addChild(self, child):
        super().addChild(child)
        # Best-effort attach without forcing a full dialog relayout
        self._attach_child_backend()

    def _clear_content(self):
        try:
            if self._content is None:
                return
            while True:
                first = self._content.get_first_child()
                if first is None:
                    break
                try:
                    self._content.remove(first)
                except Exception:
                    break
        except Exception:
            pass

    def _do_attach_now(self):
        """Synchronously attach the current child's backend widget into the Stack.

        This is the canonical attach implementation.  It is called directly from
        showChild() so the widget tree is in place before the resize is requested,
        and also scheduled via GLib.idle_add() from _attach_child_backend() for
        the asynchronous path triggered by addChild().

        Returns False so the method can be passed directly to GLib.idle_add()
        without additional wrapping (idle callbacks that return False are not
        repeated).
        """
        if self._content is None:
            return False
        try:
            # Clear previous Stack children first
            try:
                for c in list(self._content.get_children()):
                    try:
                        self._content.remove(c)
                    except Exception:
                        pass
            except Exception:
                pass
            ch = self.child()
            if ch is None:
                return False
            cw = ch.get_backend_widget()
            if cw:
                try:
                    # Wrap child in a VBox so it fills the Stack page like other backends
                    wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                    try:
                        wrapper.set_hexpand(True)
                        wrapper.set_vexpand(True)
                        try:
                            wrapper.set_halign(Gtk.Align.FILL)
                            wrapper.set_valign(Gtk.Align.FILL)
                        except Exception:
                            pass
                    except Exception:
                        pass

                    # Unparent cw from any previous container
                    try:
                        parent = cw.get_parent()
                        if parent is not None:
                            try:
                                parent.remove(cw)
                            except Exception:
                                try:
                                    cw.unparent()
                                except Exception:
                                    pass
                    except Exception:
                        pass

                    # Attach cw to the wrapper (Gtk4: append)
                    try:
                        wrapper.append(cw)
                    except Exception:
                        try:
                            wrapper.add(cw)
                        except Exception:
                            pass

                    # Encourage cw to expand/fill so layout behaves like Qt
                    try:
                        if hasattr(cw, 'set_hexpand'):
                            cw.set_hexpand(True)
                        if hasattr(cw, 'set_vexpand'):
                            cw.set_vexpand(True)
                        if hasattr(cw, 'set_halign'):
                            cw.set_halign(Gtk.Align.FILL)
                        if hasattr(cw, 'set_valign'):
                            cw.set_valign(Gtk.Align.FILL)
                    except Exception:
                        pass
                    try:
                        for inner in list(getattr(cw, 'get_children', lambda: [])()):
                            try:
                                if hasattr(inner, 'set_hexpand'):
                                    inner.set_hexpand(True)
                            except Exception:
                                pass
                            try:
                                if hasattr(inner, 'set_vexpand'):
                                    inner.set_vexpand(True)
                            except Exception:
                                pass
                            try:
                                if hasattr(inner, 'set_halign'):
                                    inner.set_halign(Gtk.Align.FILL)
                            except Exception:
                                pass
                            try:
                                if hasattr(inner, 'set_valign'):
                                    inner.set_valign(Gtk.Align.FILL)
                            except Exception:
                                pass
                    except Exception:
                        pass

                    # Second pass: remove any children added between first clear and now
                    try:
                        for c in list(self._content.get_children()):
                            try:
                                self._content.remove(c)
                            except Exception:
                                pass
                    except Exception:
                        pass

                    # Add wrapper to Stack and show it
                    name = f"child_{self._stack_page_counter}"
                    self._stack_page_counter += 1
                    try:
                        self._content.add_titled(wrapper, name, name)
                    except Exception:
                        try:
                            self._content.add(wrapper)
                        except Exception:
                            pass
                    try:
                        self._content.set_visible_child(wrapper)
                    except Exception:
                        pass
                    try:
                        wrapper.set_visible(True)
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass
        return False  # idle_add: do not repeat

    def _attach_child_backend(self):
        """Schedule the child backend attach via GLib.idle_add (no redraw).

        Called from addChild() where the child's backend widget may not yet be
        fully constructed; idle_add defers execution until the next main-loop
        iteration by which time the widget tree is ready.
        """
        if not (self._backend_widget and self._content and self.child()):
            self._logger.debug("_attach_child_backend called but no backend or no child to attach")
            return
        try:
            if self._content is None:
                self.get_backend_widget()
            if self._content is None:
                return
            # Defer so the child widget tree is fully initialised before attaching
            try:
                GLib.idle_add(self._do_attach_now)
            except Exception:
                self._do_attach_now()
        except Exception:
            pass

    def showChild(self):
        """Attach child backend synchronously, then force a dialog relayout/redraw.

        Performs the Stack attachment *synchronously* (unlike addChild which defers
        via idle_add) so the new widget is in place before queue_resize() is called.
        This prevents the window from trying to measure layout with stale content.
        """
        if not (self._backend_widget and self._content and self.child()):
            self._logger.debug("showChild called but no backend or no child to attach")
            return
        # Synchronously attach the child backend so the widget tree is up to date
        # before we trigger a layout pass.  (addChild uses idle_add which would be
        # too late when queue_resize runs at the end of this method.)
        try:
            self._do_attach_now()
        except Exception:
            self._logger.debug("showChild: _do_attach_now failed", exc_info=True)
        # Force a dialog layout/reallocation and redraw (GTK4 best-effort)
        try:
            dlg = self.findDialog()
            win = getattr(dlg, "_window", None) if dlg is not None else None
            if win is not None:
                try:
                    if hasattr(win, "queue_resize"):
                        win.queue_resize()
                except Exception:
                    pass
                try:
                    if hasattr(win, "queue_allocate"):
                        win.queue_allocate()
                except Exception:
                    pass
                try:
                    ctx = GLib.MainContext.default()
                    if ctx is not None:
                        while ctx.pending():
                            ctx.iteration(False)
                except Exception:
                    pass
                try:
                    def _idle_relayout():
                        try:
                            if hasattr(win, "queue_resize"):
                                win.queue_resize()
                        except Exception:
                            pass
                        return False
                    GLib.idle_add(_idle_relayout)
                except Exception:
                    pass
        except Exception:
            pass

    def deleteChildren(self):
        """Clear logical children and content UI for replacement."""
        try:
            self._clear_content()
            super().deleteChildren()
        except Exception as e:
            try:
                self._logger.error("deleteChildren error: %s", e, exc_info=True)
            except Exception:
                pass
