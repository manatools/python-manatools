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
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, GObject, GdkPixbuf, GLib
import cairo
import threading
import os
import logging
from ...yui_common import *

class YProgressBarGtk(YWidget):
	def __init__(self, parent=None, label="", maxValue=100):
		super().__init__(parent)
		self._label = label
		self._max_value = int(maxValue) if maxValue is not None else 100
		self._value = 0
		self._backend_widget = None
		self._label_widget = None
		self._progress_widget = None
		#default stretchable in horizontal direction
		self.setStretchable(YUIDimension.YD_HORIZ, True)
		self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")

	def widgetClass(self):
		return "YProgressBar"

	# --- size policy helpers ---
	def setStretchable(self, dimension, stretchable):
		"""Override stretchable to re-apply size policy on change using YUI base attributes."""
		try:
			super().setStretchable(dimension, stretchable)
		except Exception:
			self._logger.exception("setStretchable: base implementation failed")
		# Do not cache locally; read from base each time
		self._apply_size_policy()

	def _apply_size_policy(self):
		"""Apply GTK4 expand/alignment to container, label and progress bar using YUI stretch/weight."""
		if self._backend_widget is None:
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

			targets = []
			if getattr(self, "_backend_widget", None) is not None:
				targets.append(self._backend_widget)
			if getattr(self, "_label_widget", None) is not None:
				targets.append(self._label_widget)
			if getattr(self, "_progress_widget", None) is not None:
				targets.append(self._progress_widget)

			for w in targets:
				try:
					w.set_hexpand(eff_h)
				except Exception:
					self._logger.debug("set_hexpand failed on %s", type(w), exc_info=True)
				try:
					w.set_halign(Gtk.Align.FILL if eff_h else Gtk.Align.START)
				except Exception:
					self._logger.debug("set_halign failed on %s", type(w), exc_info=True)
				try:
					w.set_vexpand(eff_v)
				except Exception:
					self._logger.debug("set_vexpand failed on %s", type(w), exc_info=True)
				try:
					w.set_valign(Gtk.Align.FILL if eff_v else Gtk.Align.START)
				except Exception:
					self._logger.debug("set_valign failed on %s", type(w), exc_info=True)

			self._logger.debug(
				"_apply_size_policy: h_stretch=%s v_stretch=%s w_h=%s w_v=%s eff_h=%s eff_v=%s",
				h_stretch, v_stretch, w_h, w_v, eff_h, eff_v
			)
		except Exception:
			self._logger.exception("_apply_size_policy: unexpected failure")

	def label(self):
		return self._label

	def setLabel(self, newLabel):
		try:
			self._label = str(newLabel) if isinstance(newLabel, str) else newLabel
			if getattr(self, "_label_widget", None) is not None:
				try:
					is_valid = isinstance(self._label, str) and bool(self._label.strip())
					if is_valid:
						self._label_widget.set_text(self._label)
						self._label_widget.set_visible(True)
					else:
						self._label_widget.set_visible(False)
				except Exception:
					self._logger.exception("setLabel: failed to update Gtk.Label")
		except Exception:
			self._logger.exception("setLabel: unexpected error")

	def maxValue(self):
		return int(self._max_value)

	def value(self):
		return int(self._value)

	def setValue(self, newValue):
		try:
			v = int(newValue)
			if v < 0:
				v = 0
			if v > self._max_value:
				v = self._max_value
			self._value = v
			if getattr(self, "_progress_widget", None) is not None:
				try:
					self._progress_widget.set_fraction(float(self._value) / float(self._max_value) if self._max_value > 0 else 0.0)
				except Exception:
					pass
		except Exception:
			pass

	def _create_backend_widget(self):
		container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		# Start with sane defaults; final behavior comes from _apply_size_policy
		container.set_hexpand(True)
		container.set_halign(Gtk.Align.FILL)
		container.set_valign(Gtk.Align.FILL)
		# container.set_homogeneous(False)  # default; keep for clarity

		# Label
		self._label_widget = Gtk.Label()
		self._label_widget.set_halign(Gtk.Align.START)
		container.append(self._label_widget)
		try:
			is_valid = isinstance(self._label, str) and bool(self._label.strip())
			if is_valid:
				self._label_widget.set_text(self._label)
				self._label_widget.set_visible(True)
			else:
				self._label_widget.set_visible(False)
		except Exception:
			# be safe: hide if anything goes wrong
			self._label_widget.set_visible(False)

		# Progress Bar
		self._progress_widget = Gtk.ProgressBar()
		self._progress_widget.set_fraction(float(self._value) / float(self._max_value) if self._max_value > 0 else 0.0)
		self._progress_widget.set_hexpand(True)
		self._progress_widget.set_halign(Gtk.Align.FILL)
		self._progress_widget.set_show_text(True)
		container.append(self._progress_widget)

		self._backend_widget = container

		# Apply consistent size policy to avoid centered layout
		self._apply_size_policy()

		try:
			self._backend_widget.set_sensitive(self._enabled)
		except Exception:
			pass
		if self._help_text:
			try:
				self._backend_widget.set_tooltip_text(self._help_text)
			except Exception:
				self._logger.error("Failed to set tooltip text on backend widget", exc_info=True)
		try:
			self._backend_widget.set_visible(self.visible())
		except Exception:
			self._logger.error("Failed to set backend widget visible", exc_info=True)
		try:
			self._backend_widget.set_sensitive(self._enabled)
		except Exception:
			self._logger.exception("Failed to set sensitivity on backend widget")

		self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())

	def setVisible(self, visible: bool = True):
		"""Set widget visibility and propagate it to the GTK backend widget."""
		super().setVisible(visible)
		try:
			if getattr(self, "_backend_widget", None) is not None:
				self._backend_widget.set_visible(bool(visible))
		except Exception:
			self._logger.exception("setVisible failed")
	
	def setHelpText(self, help_text: str):
		"""Set help text (tooltip) and propagate it to the GTK backend widget."""
		super().setHelpText(help_text)
		try:
			if getattr(self, "_backend_widget", None) is not None:
				try:
					self._backend_widget.set_tooltip_text(help_text)
				except Exception:
					self._logger.exception("Failed to apply tooltip to backend widget")
		except Exception:
			self._logger.exception("setHelpText failed")