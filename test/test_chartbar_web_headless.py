#!/usr/bin/env python3

"""Headless end-to-end check of YChartBar on the web backend.

Boots a dialog with MUI_BACKEND=web, then talks to the real server:
- the page embeds the chart as inline SVG: one rect per non-zero bar, tick
  labels, gridlines, category labels, escaped text, a series legend;
- POST /event with data.bar selects the bar and posts an Activated
  YWidgetEvent; malformed payloads, disabled charts and notify(False) post
  nothing;
- model changes are pushed to the browser as one coalesced update
  (orientation, stacking, value labels, gridlines, empty chart).

No browser needed.  Run directly: python3 test/test_chartbar_web_headless.py
(exit 0 = pass).
"""

import json
import os
import re
import sys
import threading
import time
import urllib.request

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ["MUI_BACKEND"] = "web"

from manatools.aui.yui import YUI, YUI_ui, YChartBarOrientation, YChartLegendPosition  # noqa: E402
import manatools.aui.yui_common as yui  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
    if not cond:
        FAILURES.append(name)


def get(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.read().decode("utf-8", "replace")


def post_event(base, payload):
    req = urllib.request.Request(base + "/event", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status


def chart_html(page, chart_id):
    m = re.search(r'<div id="%s".*?</svg></div>(?:<ul.*?</ul>)?</div></div>' % re.escape(chart_id), page, re.S)
    return m.group(0) if m else ""


def updates(sent):
    return [u for m in sent if m.get("type") == "update" for u in m.get("updates", [])]


def main():
    YUI._instance = None
    YUI._backend = None
    f = YUI_ui().widgetFactory()
    dlg = f.createMainDialog()
    vbox = f.createVBox(dlg)
    chart = f.createChartBar(vbox, "Load <avg>")
    chart.setData(["Mon", "Tue & <b>Wed</b>", "Thu"],
                  ["CPU", ("RAM", "#123456")],
                  [[30, 20], [45, 0], [-10, 25]])
    f.createPushButton(vbox, "&OK")

    check("widget class", chart.widgetClass() == "YChartBar")

    threading.Thread(target=dlg.open, daemon=True).start()
    for _ in range(50):
        if getattr(getattr(dlg, "_server", None), "port", 0):
            break
        time.sleep(0.1)
    time.sleep(0.5)
    base = f"http://127.0.0.1:{dlg._server.port}"

    html = chart_html(get(base + "/"), chart.id())
    check("page: chart rendered", 'data-widget-class="YChartBar"' in html, html[:300])
    check("page: inline svg", '<svg class="mana-chartbar-svg"' in html)
    check("page: one rect per non-zero bar", html.count('class="mana-chartbar-bar') == 5,
          html.count('class="mana-chartbar-bar'))
    check("page: bar coordinates", 'data-bar="2,0"' in html and 'data-bar="1,1"' not in html)
    check("page: custom series color", 'fill="#123456"' in html)
    check("page: category escaped", "&lt;b&gt;" in html and "<b>Wed" not in html)
    check("page: title escaped", "Load &lt;avg&gt;" in html)
    check("page: ticks include 0 and negative", ">0</text>" in html and ">-10</text>" in html)
    check("page: gridlines", 'class="mana-chartbar-grid"' in html)
    check("page: zero line", 'class="mana-chartbar-zero"' in html)
    check("page: legend", html.count('class="mana-chartbar-legend-row') == 2 and ">RAM<" in html)
    check("page: no inline handlers", not re.search(r"\son[a-z]+=", html))
    check("page: no value labels by default", 'class="mana-chartbar-value' not in html)

    sent = []
    orig_broadcast = dlg._broadcast
    dlg._broadcast = lambda msg: (sent.append(msg), orig_broadcast(msg))

    # -- click ---------------------------------------------------------------
    post_event(base, {"type": "event", "widget_id": chart.id(), "reason": "Activated",
                      "data": {"bar": [2, 1]}})
    ev = dlg.waitForEvent(2000)
    check("click: event posted", ev.eventType() == yui.YEventType.WidgetEvent
          and ev.widget() is chart and ev.reason() == yui.YEventReason.Activated,
          (ev.eventType(), ev.widget()))
    check("click: bar selected", (chart.selectedCategory(), chart.selectedSeries()) == (2, 1))
    time.sleep(0.3)
    check("click: selection pushed", any("mana-chartbar-selected" in json.dumps(m) for m in sent))
    ups = updates(sent)
    check("click: selection is attr-only", ups and all(u.get("action") == "attr" for u in ups)
          and any(u["target"].endswith('rect[data-bar="2,1"]') and "selected" in u["value"] for u in ups)
          and any(u["target"].endswith('li[data-series="1"]') for u in ups), ups)

    for bad in ([9, 0], [0, 9], [-1, 0], [0], [0, 1, 2], "0,1", None, [True, 0], [0.5, 1], {"c": 0}):
        post_event(base, {"type": "event", "widget_id": chart.id(), "reason": "Activated",
                          "data": {"bar": bad}})
    ev = dlg.waitForEvent(500)
    check("click: bad payloads ignored", ev.eventType() == yui.YEventType.TimeoutEvent
          and (chart.selectedCategory(), chart.selectedSeries()) == (2, 1),
          (ev.eventType(), chart.selectedCategory(), chart.selectedSeries()))

    chart.setEnabled(False)
    post_event(base, {"type": "event", "widget_id": chart.id(), "data": {"bar": [0, 0]}})
    ev = dlg.waitForEvent(500)
    check("click: disabled ignored", ev.eventType() == yui.YEventType.TimeoutEvent
          and chart.selectedCategory() == 2)
    chart.setEnabled(True)

    chart.setNotify(False)
    post_event(base, {"type": "event", "widget_id": chart.id(), "data": {"bar": [0, 0]}})
    ev = dlg.waitForEvent(500)
    check("click: notify off selects, no event", ev.eventType() == yui.YEventType.TimeoutEvent
          and (chart.selectedCategory(), chart.selectedSeries()) == (0, 0))
    chart.setNotify(True)

    # -- live updates --------------------------------------------------------
    time.sleep(0.3)
    sent.clear()
    chart.setOrientation(YChartBarOrientation.Horizontal)
    chart.setStacked(True)
    chart.setShowValues(True)
    chart.setShowGrid(False)
    chart.setValue(1, 1, 1500)
    chart.setLegendPosition(YChartLegendPosition.Bottom)
    time.sleep(0.4)
    ups = updates(sent)
    check("update: coalesced to one", len(ups) == 1, len(ups))
    upd = ups[0]["html"] if ups else ""
    check("update: horizontal + legend bottom", "mana-chartbar-horizontal" in upd
          and "mana-chartbar-legend-bottom" in upd)
    check("update: value labels", 'class="mana-chartbar-value' in upd and ">1500</text>" in upd)
    check("update: compact ticks", "k</text>" in upd, re.findall(r'tick"[^>]*>([^<]*)<', upd))
    check("update: no gridlines", 'class="mana-chartbar-grid"' not in upd
          and 'class="mana-chartbar-zero"' in upd)
    check("update: stacked bars share width",
          len(set(re.findall(r'data-bar="1,\d"[^>]*?y="([\d.]+)"', upd))) == 1,
          re.findall(r'data-bar="1,\d"[^>]*?y="([\d.]+)"', upd))

    sent.clear()
    chart.deleteAllData()
    time.sleep(0.3)
    upd = json.dumps(sent)
    check("empty: No data", "mana-chartbar-empty" in upd and "No data" in upd
          and "mana-chartbar-bar" not in upd)

    try:
        chart.addSeries("bad", '#000" onload="x')
        check("color: injection rejected", False)
    except ValueError:
        check("color: injection rejected", True)

    # -- a failing chart must not break the page --------------------------------
    chart.setData(["a"], ["s"], [[1]])
    real = chart._render_svg
    chart._render_svg = lambda: 1 / 0
    try:
        page = get(base + "/")
        check("render error: page still served", "Chart unavailable" in page and "mana-ychartbar" in page)
    except Exception as e:
        check("render error: page still served", False, e)
    chart._render_svg = real

    dlg.destroy()
    print("FAILED: " + ", ".join(FAILURES) if FAILURES else "all passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
