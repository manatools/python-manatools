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
		self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")

	def widgetClass(self):
		return "YProgressBar"

	def label(self):
		return self._label

	def setLabel(self, newLabel):
		try:
			self._label = str(newLabel)
			if getattr(self, "_label_widget", None) is not None:
				try:
					self._label_widget.set_text(self._label)
				except Exception:
					pass
		except Exception:
			pass

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
		container.set_hexpand(True)
		container.set_halign(Gtk.Align.FILL)

		# Label
		self._label_widget = Gtk.Label(label=self._label)
		self._label_widget.set_halign(Gtk.Align.START)
		container.append(self._label_widget)

		# Progress Bar
		self._progress_widget = Gtk.ProgressBar()
		self._progress_widget.set_fraction(float(self._value) / float(self._max_value) if self._max_value > 0 else 0.0)
		self._progress_widget.set_hexpand(True)
		self._progress_widget.set_halign(Gtk.Align.FILL)
		self._progress_widget.set_show_text(True)
		container.append(self._progress_widget)

		self._backend_widget = container
		try:
			self._backend_widget.set_sensitive(self._enabled)
		except Exception:
			pass
		try:
			self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
		except Exception:
			pass