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

class YProgressBarQt(YWidget):
	"""Qt6 (PySide6) progress bar with optional label above it.
	Provides value/max management and respects visibility and tooltip (help text).
	"""

	def __init__(self, parent=None, label="", maxValue=100):
		super().__init__(parent)
		self._label = label
		self._max_value = int(maxValue) if maxValue is not None else 100
		self._value = 0
		self._backend_widget = None
		self._label_widget = None
		self._progress_widget = None
		self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")

	def widgetClass(self):
		return "YProgressBar"

	def label(self):
		return self._label

	def setLabel(self, newLabel):
		try:
			self._label = str(newLabel) if isinstance(newLabel, str) else newLabel
			if getattr(self, "_label_widget", None) is not None:
				try:
					is_valid = isinstance(self._label, str) and bool(self._label.strip())
					if is_valid:
						self._label_widget.setText(self._label)
						self._label_widget.setVisible(True)
					else:
						# hide the label if not a valid string
						self._label_widget.setVisible(False)
				except Exception:
					self._logger.exception("setLabel: failed to update QLabel")
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
					self._progress_widget.setValue(self._value)
				except Exception:
					pass
		except Exception:
			pass

	def _create_backend_widget(self):
		try:
			container = QtWidgets.QWidget()
			layout = QtWidgets.QVBoxLayout(container)
			layout.setContentsMargins(0, 0, 0, 0)
			layout.setSpacing(0)

			# container vertical stretching is allowed only if widget is stretchable vertically
			h_policy = QtWidgets.QSizePolicy.Expanding if self.stretchable(YUIDimension.YD_HORIZ) else QtWidgets.QSizePolicy.Preferred
			v_policy = QtWidgets.QSizePolicy.Expanding if self.stretchable(YUIDimension.YD_VERT) else QtWidgets.QSizePolicy.Fixed
			container.setSizePolicy(h_policy, v_policy)

			# Place label above the progress bar; always create then show/hide based on validity
			lbl = QtWidgets.QLabel()
			lbl.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
			layout.addWidget(lbl)
			try:
				is_valid = isinstance(self._label, str) and bool(self._label.strip())
				if is_valid:
					lbl.setText(self._label)
					lbl.setVisible(True)
				else:
					lbl.setVisible(False)
			except Exception:
				# be safe: hide if anything goes wrong
				lbl.setVisible(False)

			prog = QtWidgets.QProgressBar()
			prog.setRange(0, max(1, int(self._max_value)))
			prog.setValue(int(self._value))
			prog.setTextVisible(True)
			# progress bar horizontal expand; vertical policy mirrors container vertical policy
			prog.setSizePolicy(QtWidgets.QSizePolicy.Expanding, 
					  QtWidgets.QSizePolicy.Expanding if self.stretchable(YUIDimension.YD_VERT) else QtWidgets.QSizePolicy.Fixed)
			layout.addWidget(prog)

			self._backend_widget = container
			self._label_widget = lbl
			self._progress_widget = prog
			self._backend_widget.setEnabled(bool(self._enabled))
			# Apply initial tooltip and visibility like other Qt widgets (e.g., combobox)
			try:
				if getattr(self, "_help_text", None):
					try:
						self._backend_widget.setToolTip(self._help_text)
					except Exception:
						self._logger.exception("Failed to set tooltip on progressbar")
			except Exception:
				self._logger.exception("Tooltip setup error on progressbar")
			try:
				self._backend_widget.setVisible(self.visible())
			except Exception:
				self._logger.exception("Failed to set initial visibility on progressbar")
			try:
				self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
			except Exception:
				pass
		except Exception:
			self._backend_widget = None
			self._label_widget = None
			self._progress_widget = None
			self._logger.exception("_create_backend_widget failed")

	def _set_backend_enabled(self, enabled):
		try:
			if getattr(self, "_backend_widget", None) is not None:
				try:
					self._backend_widget.setEnabled(bool(enabled))
				except Exception:
					pass
		except Exception:
			pass

	def setProperty(self, propertyName, val):
		try:
			if propertyName == "label":
				self.setLabel(str(val))
				return True
			if propertyName == "value":
				try:
					self.setValue(int(val))
				except Exception:
					# if val is YPropertyValue
					try:
						self.setValue(int(val.integerVal()))
					except Exception:
						pass
				return True
		except Exception:
			pass
		return False

	def getProperty(self, propertyName):
		try:
			if propertyName == "label":
				return self.label()
			if propertyName == "value":
				return self.value()
			if propertyName == "maxValue":
				return self.maxValue()
		except Exception:
			pass
		return None

	def propertySet(self):
		try:
			props = YPropertySet()
			try:
				props.add(YProperty("label", YPropertyType.YStringProperty))
				props.add(YProperty("value", YPropertyType.YIntegerProperty))
				props.add(YProperty("maxValue", YPropertyType.YIntegerProperty))
			except Exception:
				pass
			return props
		except Exception:
			return None

	def stretchable(self, dim: YUIDimension):
		# Progress bars usually expand horizontally but not vertically
		try:
			if dim == YUIDimension.YD_HORIZ:
				return True
			return False
		except Exception:
			return False

	def setVisible(self, visible=True):
		"""Set widget visibility and propagate it to the Qt backend widget."""
		super().setVisible(visible)
		try:
			if getattr(self, "_backend_widget", None) is not None:
				self._backend_widget.setVisible(bool(visible))
		except Exception:
			self._logger.exception("setVisible failed")

	def setHelpText(self, help_text: str):
		"""Set help text (tooltip) and propagate it to the Qt backend widget."""
		super().setHelpText(help_text)
		try:
			if getattr(self, "_backend_widget", None) is not None:
				try:
					self._backend_widget.setToolTip(help_text)
				except Exception:
					self._logger.exception("Failed to apply tooltip to backend widget")
		except Exception:
			self._logger.exception("setHelpText failed")
