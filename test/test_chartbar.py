#!/usr/bin/env python3

"""YChartBar demo: a bar chart that changes at runtime and reports bar clicks.

Run with a backend name or MUI_BACKEND:
    python3 test/test_chartbar.py web|qt|gtk|ncurses
"""

import os
import random
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
SERIES = ["CPU", "RAM", ("Swap", "#cc0000")]
ROWS = [[30, 20, 5], [45, 25, -8], [28, 40, 12], [60, 15, -20], [52, 33, 7], [70, 10, 15]]
EXTRA = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def test_chartbar(backend_name=None):
    if backend_name:
        print(f"Setting backend to: {backend_name}")
        os.environ['MUI_BACKEND'] = backend_name
    else:
        print("Using auto-detection")
    try:
        from manatools.aui.yui import YUI, YUI_ui, YChartBarOrientation, YChartLegendPosition
        import manatools.aui.yui_common as yui

        backend = YUI.backend()
        print(f"Using backend: {backend.value}")

        ui = YUI_ui()
        factory = ui.widgetFactory()
        ui.application().setApplicationTitle(f"YChartBar {backend.value} demo")
        dialog = factory.createMainDialog()

        vbox = factory.createVBox(dialog)
        chart = factory.createChartBar(vbox, "Load (%)")
        chart.setData(MONTHS, SERIES, ROWS)
        chart.setHelpText("Click a bar")

        status = factory.createLabel(vbox, "Click a bar")
        status.setStretchable(yui.YUIDimension.YD_HORIZ, True)

        row1 = factory.createHBox(vbox)
        add_btn = factory.createPushButton(row1, "Add month")
        rand_btn = factory.createPushButton(row1, "Randomize")
        clear_btn = factory.createPushButton(row1, "Clear")
        reset_btn = factory.createPushButton(row1, "Reset")

        row2 = factory.createHBox(vbox)
        horiz_cb = factory.createCheckBox(row2, "Horizontal", False)
        stack_cb = factory.createCheckBox(row2, "Stacked", False)
        values_cb = factory.createCheckBox(row2, "Values", False)
        grid_cb = factory.createCheckBox(row2, "Grid", True)
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
            if w is chart:
                c, s = chart.selectedCategory(), chart.selectedSeries()
                if c >= 0:
                    status.setValue(f"Clicked: {chart.categoryLabel(c)} / {chart.seriesName(s)}"
                                    f" = {chart.value(c, s):g}"
                                    f" (category total {chart.categoryTotal(c):g})")
            elif w is add_btn:
                n = chart.categoryCount()
                label = EXTRA[n % len(EXTRA)] if n >= len(MONTHS) else f"M{n + 1}"
                chart.addCategory(label, [random.randint(-10, 80) for _ in range(chart.seriesCount())])
            elif w is rand_btn:
                rows = [[random.randint(-20, 80) for _ in range(chart.seriesCount())]
                        for _ in range(chart.categoryCount())]
                chart.setData([chart.categoryLabel(c) for c in range(chart.categoryCount())],
                              [(chart.seriesName(s), chart.seriesColor(s)) for s in range(chart.seriesCount())],
                              rows)
            elif w is clear_btn:
                chart.deleteAllData()
                status.setValue("Cleared")
            elif w is reset_btn:
                chart.setData(MONTHS, SERIES, ROWS)
                status.setValue("Reset")
            elif w is horiz_cb:
                chart.setOrientation(YChartBarOrientation.Horizontal if horiz_cb.isChecked()
                                     else YChartBarOrientation.Vertical)
            elif w is stack_cb:
                chart.setStacked(stack_cb.isChecked())
            elif w is values_cb:
                chart.setShowValues(values_cb.isChecked())
            elif w is grid_cb:
                chart.setShowGrid(grid_cb.isChecked())
            elif w is legend_combo:
                item = legend_combo.selectedItem()
                if item is not None:
                    chart.setLegendPosition(YChartLegendPosition[item.label()])

        dialog.destroy()

    except Exception as e:
        print(f"Error testing ChartBar with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_chartbar(sys.argv[1])
    else:
        test_chartbar()
