# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.qt contains all Qt backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.qt
'''
from PySide6 import QtWidgets
from ...yui_common import *

class YProgressBarQt(YWidget):
	def __init__(self, parent=None, label="", maxValue=100):
		super().__init__(parent)
		self._label = label
		self._max_value = int(maxValue) if maxValue is not None else 100
		self._value = 0
		self._backend_widget = None
		self._label_widget = None
		self._progress_widget = None

	def widgetClass(self):
		return "YProgressBar"

	def label(self):
		return self._label

	def setLabel(self, newLabel):
		try:
			self._label = str(newLabel)
			if getattr(self, "_label_widget", None) is not None:
				try:
					self._label_widget.setText(self._label)
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

			# Place label above the progress bar with no spacing so they remain attached
			lbl = QtWidgets.QLabel(self._label) if self._label else None
			if lbl is not None:
				lbl.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
				layout.addWidget(lbl)

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
		except Exception:
			self._backend_widget = None
			self._label_widget = None
			self._progress_widget = None

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
