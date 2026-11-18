#!/usr/bin/env python3

"""YChartGauge demo: gauges that change at runtime and report clicks.

Run with a backend name or MUI_BACKEND:
    python3 test/test_chartgauge.py web|qt|gtk|ncurses
"""

import os
import random
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BANDS = [(0, 60, None, "Normal"), (60, 85, None, "High"), (85, 100, None, "Critical")]


def test_chartgauge(backend_name=None):
    if backend_name:
        print(f"Setting backend to: {backend_name}")
        os.environ['MUI_BACKEND'] = backend_name
    else:
        print("Using auto-detection")
    try:
        from manatools.aui.yui import YUI, YUI_ui, YChartLegendPosition
        import manatools.aui.yui_common as yui

        backend = YUI.backend()
        print(f"Using backend: {backend.value}")

        ui = YUI_ui()
        factory = ui.widgetFactory()
        ui.application().setApplicationTitle(f"YChartGauge {backend.value} demo")
        dialog = factory.createMainDialog()

        vbox = factory.createVBox(dialog)
        gauges = factory.createHBox(vbox)
        cpu = factory.createChartGauge(gauges, "CPU load")
        cpu.setBands(BANDS)
        cpu.setValue(42)
        cpu.setUnit("%")
        cpu.setDecimals(0)
        cpu.setSubtitle("1 min average")
        cpu.setTarget(75)
        cpu.setHelpText("Click the dial")

        temp = factory.createChartGauge(gauges, "Temperature")
        temp.setRange(-20, 40)
        temp.setBands([(-20, 0, "#56b4e9", "Freezing"), (30, 40, "#d55e00", "Hot")])
        temp.setValue(-5)
        temp.setUnit(" °C")
        temp.setDecimals(1)
        temp.setShowNeedle(True)
        temp.setSweepAngle(180)
        temp.setLegendPosition(YChartLegendPosition.Bottom)

        status = factory.createLabel(vbox, "Click a gauge")
        status.setStretchable(yui.YUIDimension.YD_HORIZ, True)

        row1 = factory.createHBox(vbox)
        rand_btn = factory.createPushButton(row1, "Randomize")
        over_btn = factory.createPushButton(row1, "Overflow")
        sweep_combo = factory.createComboBox(row1, "Sweep")
        for deg in ("180", "240", "300"):
            sweep_combo.addItem(yui.YItem(deg, deg == "240"))

        row2 = factory.createHBox(vbox)
        needle_cb = factory.createCheckBox(row2, "Needle", False)
        ticks_cb = factory.createCheckBox(row2, "Ticks", True)
        value_cb = factory.createCheckBox(row2, "Value", True)
        target_cb = factory.createCheckBox(row2, "Target", True)
        legend_combo = factory.createComboBox(row2, "Legend")
        legend_combo.addItem(yui.YItem("Right", True))
        legend_combo.addItem(yui.YItem("Bottom"))
        legend_combo.addItem(yui.YItem("Hidden"))
        quit_btn = factory.createPushButton(vbox, "Quit")

        dialog.open()
        while True:
            ev = dialog.waitForEvent()
            if ev.eventType() == yui.YEventType.CancelEvent:
                break
            if ev.eventType() != yui.YEventType.WidgetEvent:
                continue
            w = ev.widget()
            if w is quit_btn:
                break
            if w in (cpu, temp):
                status.setValue(f"Clicked: {w.label()} = {w.value():g}{w.unit()}")
            elif w is rand_btn:
                cpu.setValue(random.uniform(0, 100))
                temp.setValue(random.uniform(-20, 40))
            elif w is over_btn:
                # Outside the range: the dial stops at the end, the text shows the real value.
                cpu.setValue(130)
                temp.setValue(-35)
            elif w is sweep_combo:
                item = sweep_combo.selectedItem()
                if item is not None:
                    cpu.setSweepAngle(int(item.label()))
            elif w is needle_cb:
                cpu.setShowNeedle(needle_cb.isChecked())
            elif w is ticks_cb:
                cpu.setShowTicks(ticks_cb.isChecked())
                temp.setShowTicks(ticks_cb.isChecked())
            elif w is value_cb:
                cpu.setShowValue(value_cb.isChecked())
                temp.setShowValue(value_cb.isChecked())
            elif w is target_cb:
                cpu.setTarget(75 if target_cb.isChecked() else None)
            elif w is legend_combo:
                item = legend_combo.selectedItem()
                if item is not None:
                    cpu.setLegendPosition(YChartLegendPosition[item.label()])

        dialog.destroy()

    except Exception as e:
        print(f"Error testing ChartGauge with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_chartgauge(sys.argv[1])
    else:
        test_chartgauge()
