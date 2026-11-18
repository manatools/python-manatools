#!/usr/bin/env python3

"""YChartPie demo: a pie that changes at runtime and reports slice clicks.

Run with a backend name or MUI_BACKEND:
    python3 test/test_chartpie.py web|qt|gtk|ncurses
"""

import os
import random
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

SAMPLE = [("System", 18.5), ("Home", 42), ("Cache", 7.25), ("Logs", 3), ("Free", 29.25)]


def test_chartpie(backend_name=None):
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
        ui.application().setApplicationTitle(f"YChartPie {backend.value} demo")
        dialog = factory.createMainDialog()

        vbox = factory.createVBox(dialog)
        chart = factory.createChartPie(vbox, "Disk usage (GB)")
        chart.setSlices(SAMPLE)
        chart.setHelpText("Click a slice or a legend row")

        status = factory.createLabel(vbox, "Click a slice")
        status.setStretchable(yui.YUIDimension.YD_HORIZ, True)

        hbox = factory.createHBox(vbox)
        add_btn = factory.createPushButton(hbox, "Add")
        rand_btn = factory.createPushButton(hbox, "Randomize")
        clear_btn = factory.createPushButton(hbox, "Clear")
        donut_cb = factory.createCheckBox(hbox, "Donut", False)
        legend_combo = factory.createComboBox(hbox, "Legend")
        legend_combo.addItem(yui.YItem("Right", True))
        legend_combo.addItem(yui.YItem("Bottom"))
        legend_combo.addItem(yui.YItem("Hidden"))
        pct_cb = factory.createCheckBox(hbox, "Percent", True)
        quit_btn = factory.createPushButton(vbox, "Quit")

        def update_center():
            chart.setCenterText(f"{chart.total():g}")

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
            if w is chart:
                i = chart.selectedSlice()
                if i >= 0:
                    s = chart.slice(i)
                    status.setValue(f"Clicked: {s.label()} = {s.value():g} "
                                    f"({chart.slicePercent(i):.1f}%)")
            elif w is add_btn:
                n = chart.sliceCount() + 1
                chart.addSlice(f"Extra {n}", random.randint(1, 30))
                update_center()
            elif w is rand_btn:
                for i in range(chart.sliceCount()):
                    chart.setSliceValue(i, random.randint(0, 50))
                update_center()
            elif w is clear_btn:
                chart.deleteAllSlices()
                status.setValue("Cleared")
                update_center()
            elif w is donut_cb:
                chart.setDonutRatio(0.55 if donut_cb.isChecked() else 0.0)
                update_center()
            elif w is pct_cb:
                chart.setShowPercent(pct_cb.isChecked())
            elif w is legend_combo:
                item = legend_combo.selectedItem()
                if item is not None:
                    chart.setLegendPosition(YChartLegendPosition[item.label()])

        dialog.destroy()

    except Exception as e:
        print(f"Error testing ChartPie with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_chartpie(sys.argv[1])
    else:
        test_chartpie()
