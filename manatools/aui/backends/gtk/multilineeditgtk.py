# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.gtk contains GTK backend for YMultiLineEdit

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
'''
import logging
import gi
try:
    gi.require_version('Gtk', '4.0')
    from gi.repository import Gtk, GLib
except Exception:
    Gtk = None
    GLib = None

from ...yui_common import *

_mod_logger = logging.getLogger("manatools.aui.gtk.multiline.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)


class YMultiLineEditGtk(YWidget):
    def __init__(self, parent=None, label=""):
        super().__init__(parent)
        self._label = label
        self._value = ""
        # default visible content lines (consistent across backends)
        self._default_visible_lines = 3
        # -1 means no input length limit
        self._input_max_length = -1
        # reported minimal height: content lines + label row (if present)
        self._height = self._default_visible_lines + (1 if bool(self._label) else 0)
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        if not self._logger.handlers and _mod_logger.handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)

        self._widget = None

    def widgetClass(self):
        return "YMultiLineEdit"

    def value(self):
        return str(self._value)

    def inputMaxLength(self):
        return int(getattr(self, '_input_max_length', -1))

    def setInputMaxLength(self, numberOfChars):
        try:
            self._input_max_length = int(numberOfChars)
        except Exception:
            self._input_max_length = -1
        try:
            if self._widget is not None and self._input_max_length >= 0:
                buf = self._textview.get_buffer()
                start = buf.get_start_iter()
                end = buf.get_end_iter()
                try:
                    text = buf.get_text(start, end, True)
                except Exception:
                    text = ""
                if len(text) > self._input_max_length:
                    try:
                        buf.set_text(text[:self._input_max_length])
                        self._value = text[:self._input_max_length]
                    except Exception:
                        pass
        except Exception:
            pass

    def setValue(self, text):
        try:
            s = str(text) if text is not None else ""
        except Exception:
            s = ""
        self._value = s
        try:
            if self._widget is not None:
                buf = self._textview.get_buffer()
                try:
                    buf.set_text(self._value)
                except Exception:
                    pass
        except Exception:
            pass

    def label(self):
        return self._label

    def setLabel(self, label):
        try:
            self._label = label
            if self._widget is not None:
                try:
                    self._lbl.set_text(str(label))
                except Exception:
                    pass
        except Exception:
            pass

    def defaultVisibleLines(self):
        return int(getattr(self, '_default_visible_lines', 3))

    def setDefaultVisibleLines(self, newVisibleLines):
        try:
            self._default_visible_lines = int(newVisibleLines)
            self._height = self._default_visible_lines + (1 if bool(self._label) else 0)
            try:
                # Re-apply sizing based on new visible lines
                self._apply_stretch_policy()
            except Exception:
                pass
        except Exception:
            pass

    def setStretchable(self, dim, new_stretch):
        try:
            super().setStretchable(dim, new_stretch)
        except Exception:
            pass
        try:
            # Re-apply full policy so axes are handled independently
            self._apply_stretch_policy()
        except Exception:
            pass

    def _create_backend_widget(self):
        try:
            if Gtk is None:
                raise ImportError("GTK not available")
            box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
            self._lbl = Gtk.Label.new(str(self._label))
            # Use scrolled window so when expanded beyond screen scrollbars appear
            try:
                self._scrolled = Gtk.ScrolledWindow.new()
                self._textview = Gtk.TextView.new()
                self._scrolled.set_child(self._textview)
            except Exception:
                self._scrolled = None
                self._textview = Gtk.TextView.new()
            try:
                buf = self._textview.get_buffer()
                buf.set_text(self._value)
                try:
                    self._buf_handler_id = buf.connect('changed', self._on_buffer_changed)
                except Exception:
                    self._buf_handler_id = None
            except Exception:
                pass
            box.append(self._lbl)
            if getattr(self, '_scrolled', None) is not None:
                box.append(self._scrolled)
            else:
                box.append(self._textview)
            self._widget = box
            self._backend_widget = self._widget
            try:
                # Apply initial stretch/min size policy
                self._apply_stretch_policy()
            except Exception:
                pass
        except Exception as e:
            try:
                self._logger.exception("Error creating GTK MultiLineEdit backend: %s", e)
            except Exception:
                pass

    def _set_backend_enabled(self, enabled):
        try:
            if self._widget is not None:
                try:
                    self._textview.set_sensitive(enabled)
                except Exception:
                    pass
        except Exception:
            pass

    def _on_buffer_changed(self, buf):
        try:
            start = buf.get_start_iter()
            end = buf.get_end_iter()
            try:
                text = buf.get_text(start, end, True)
            except Exception:
                text = ""
            # enforce input max length
            try:
                if getattr(self, '_input_max_length', -1) >= 0 and len(text) > self._input_max_length:
                    try:
                        if getattr(self, '_buf_handler_id', None) is not None:
                            buf.handler_block(self._buf_handler_id)
                    except Exception:
                        pass
                    try:
                        buf.set_text(text[:self._input_max_length])
                        text = text[:self._input_max_length]
                    except Exception:
                        pass
                    try:
                        if getattr(self, '_buf_handler_id', None) is not None:
                            buf.handler_unblock(self._buf_handler_id)
                    except Exception:
                        pass
            except Exception:
                pass
            self._value = text
            dlg = self.findDialog()
            if dlg is not None:
                try:
                    if self.notify():
                        dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
                except Exception:
                    try:
                        self._logger.exception("Failed to post ValueChanged event")
                    except Exception:
                        pass
        except Exception:
            try:
                self._logger.exception("_on_buffer_changed error")
            except Exception:
                pass

    def _apply_stretch_policy(self):
        """Apply horizontal/vertical stretch independently and set min pixel sizes.

        - When an axis is not stretchable, set a minimum pixel size:
          width ~= 20 chars; height ~= `defaultVisibleLines` lines + label.
        - When stretchable, clear size requests and set expand flags.
        """
        try:
            if self._widget is None:
                return
            target = self._scrolled if getattr(self, '_scrolled', None) is not None else self._textview

            # Determine current stretch flags
            horiz = bool(self.stretchable(YUIDimension.YD_HORIZ))
            vert = bool(self.stretchable(YUIDimension.YD_VERT))

            # Compute approximate character width and line height via Pango
            try:
                layout = self._textview.create_pango_layout("M") if self._textview is not None else None
                if layout is not None:
                    char_w, line_h = layout.get_pixel_size()
                else:
                    char_w, line_h = 8, 16
                # Fallback if layout reports zeros
                if not char_w:
                    char_w = 8
                if not line_h:
                    line_h = 16
            except Exception:
                char_w, line_h = 8, 16

            # Label height approximation
            try:
                lbl_layout = self._lbl.create_pango_layout("M") if self._lbl is not None else None
                qlabel_w, qlabel_h = lbl_layout.get_pixel_size() if lbl_layout is not None else (0, 20)
                if not qlabel_h:
                    qlabel_h = 20
            except Exception:
                qlabel_h = 20

            desired_chars = 20
            w_px = int(char_w * desired_chars) + 12
            text_h_px = int(line_h * max(1, self._default_visible_lines))
            box_h_px = text_h_px + qlabel_h + 8

            # Expansion flags
            try:
                if target is not None:
                    target.set_hexpand(horiz)
                    target.set_vexpand(vert)
                self._widget.set_hexpand(horiz)
                self._widget.set_vexpand(vert)
            except Exception:
                pass

            # Horizontal constraint
            try:
                if not horiz:
                    if target is not None and hasattr(target, 'set_min_content_width'):
                        target.set_min_content_width(w_px)
                    else:
                        # Fallback
                        if target is not None:
                            target.set_size_request(w_px, -1)
                        else:
                            self._widget.set_size_request(w_px, -1)
                else:
                    if target is not None:
                        target.set_size_request(-1, -1)
            except Exception:
                pass

            # Vertical constraint
            try:
                if not vert:
                    if target is not None and hasattr(target, 'set_min_content_height'):
                        target.set_min_content_height(text_h_px)
                    else:
                        if target is not None:
                            target.set_size_request(-1, text_h_px)
                    # Ensure overall box accounts for label rows
                    try:
                        self._widget.set_size_request(-1, box_h_px)
                    except Exception:
                        pass
                else:
                    if target is not None:
                        target.set_size_request(-1, -1)
                    try:
                        self._widget.set_size_request(-1, -1)
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            try:
                self._logger.exception("_apply_stretch_policy failed")
            except Exception:
                pass
