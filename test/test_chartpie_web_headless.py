#!/usr/bin/env python3

"""Headless end-to-end check of YChartPie on the web backend.

Boots a dialog with MUI_BACKEND=web, then talks to the real server:
- the page embeds the chart as inline SVG with one path per non-zero slice,
  a legend row per slice and escaped labels;
- POST /event with data.slice selects the slice and posts an Activated
  YWidgetEvent; bad indices, disabled charts and notify(False) post nothing;
- model changes are pushed to the browser as one coalesced update.

No browser needed.  Run directly: python3 test/test_chartpie_web_headless.py
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

from manatools.aui.yui import YUI, YUI_ui, YChartLegendPosition  # noqa: E402
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


def sent_updates(sent):
    return [u for m in sent if m.get("type") == "update" for u in m.get("updates", [])]


def chart_html(page, chart_id):
    m = re.search(r'<div id="%s".*?</ul></div></div>' % re.escape(chart_id), page, re.S)
    return m.group(0) if m else ""


def main():
    YUI._instance = None
    YUI._backend = None
    f = YUI_ui().widgetFactory()
    dlg = f.createMainDialog()
    vbox = f.createVBox(dlg)
    chart = f.createChartPie(vbox, "Disk <usage>")
    chart.addSlice("System", 40)
    chart.addSlice("Home & <b>data</b>", 35, "#123456")
    chart.addSlice("Empty", 0)
    chart.addSlice("Free", 25)
    f.createPushButton(vbox, "&OK")

    check("widget class", chart.widgetClass() == "YChartPie")

    threading.Thread(target=dlg.open, daemon=True).start()
    for _ in range(50):
        if getattr(getattr(dlg, "_server", None), "port", 0):
            break
        time.sleep(0.1)
    time.sleep(0.5)
    base = f"http://127.0.0.1:{dlg._server.port}"

    html = chart_html(get(base + "/"), chart.id())
    check("page: chart rendered", 'data-widget-class="YChartPie"' in html, html[:300])
    check("page: inline svg", '<svg class="mana-chartpie-svg"' in html)
    check("page: one path per non-zero slice", html.count('class="mana-chartpie-slice') == 3)
    check("page: legend row per slice", html.count('class="mana-chartpie-legend-row') == 4)
    check("page: custom color", 'fill="#123456"' in html)
    check("page: label escaped", "&lt;b&gt;data&lt;/b&gt;" in html and "<b>data" not in html)
    check("page: title escaped", "Disk &lt;usage&gt;" in html)
    check("page: no inline handlers", not re.search(r"\son[a-z]+=", html))
    check("page: percent shown", "40.0%" in html)

    sent = []
    orig_broadcast = dlg._broadcast
    dlg._broadcast = lambda msg: (sent.append(msg), orig_broadcast(msg))

    # -- click ---------------------------------------------------------------
    post_event(base, {"type": "event", "widget_id": chart.id(), "reason": "Activated",
                      "data": {"slice": 3}})
    ev = dlg.waitForEvent(2000)
    check("click: event posted", ev.eventType() == yui.YEventType.WidgetEvent
          and ev.widget() is chart and ev.reason() == yui.YEventReason.Activated,
          (ev.eventType(), ev.widget()))
    check("click: slice selected", chart.selectedSlice() == 3, chart.selectedSlice())
    time.sleep(0.3)
    check("click: selection pushed", any("mana-chartpie-selected" in json.dumps(m) for m in sent))
    ups = sent_updates(sent)
    check("click: selection is attr-only", ups and all(u.get("action") == "attr" for u in ups)
          and any(u["target"].endswith('path[data-slice="3"]') and "selected" in u["value"] for u in ups),
          ups)

    for bad in (99, -1, "x", None, True, [1], 1.5):
        post_event(base, {"type": "event", "widget_id": chart.id(), "reason": "Activated",
                          "data": {"slice": bad}})
    ev = dlg.waitForEvent(500)
    check("click: bad indices ignored", ev.eventType() == yui.YEventType.TimeoutEvent
          and chart.selectedSlice() == 3, (ev.eventType(), chart.selectedSlice()))

    chart.setEnabled(False)
    post_event(base, {"type": "event", "widget_id": chart.id(), "data": {"slice": 0}})
    ev = dlg.waitForEvent(500)
    check("click: disabled ignored", ev.eventType() == yui.YEventType.TimeoutEvent
          and chart.selectedSlice() == 3)
    chart.setEnabled(True)

    chart.setNotify(False)
    post_event(base, {"type": "event", "widget_id": chart.id(), "data": {"slice": 0}})
    ev = dlg.waitForEvent(500)
    check("click: notify off selects, no event", ev.eventType() == yui.YEventType.TimeoutEvent
          and chart.selectedSlice() == 0)
    chart.setNotify(True)

    # -- live updates --------------------------------------------------------
    time.sleep(0.3)
    sent.clear()
    chart.setDonutRatio(0.5)
    chart.setCenterText("75 GB")
    chart.setSliceValue(0, 10)
    chart.setLegendPosition(YChartLegendPosition.Bottom)
    time.sleep(0.4)
    updates = [u for m in sent if m.get("type") == "update" for u in m.get("updates", [])]
    check("update: coalesced to one", len(updates) == 1, len(updates))
    upd = updates[0]["html"] if updates else ""
    check("update: center text", "75 GB" in upd)
    check("update: legend bottom", "mana-chartpie-legend-bottom" in upd)
    check("update: new percent", "14.3%" in upd, re.findall(r"[\d.]+%", upd))

    sent.clear()
    chart.deleteAllSlices()
    time.sleep(0.3)
    upd = json.dumps(sent)
    check("empty: no data ring", "mana-chartpie-empty" in upd and "No data" in upd)

    try:
        chart.addSlice("bad", 1, '#000" onload="x')
        check("color: injection rejected", False)
    except ValueError:
        check("color: injection rejected", True)

    # -- a failing chart must not break the page --------------------------------
    chart.addSlice("x", 1)
    real = chart._render_svg
    chart._render_svg = lambda: 1 / 0
    try:
        page = get(base + "/")
        check("render error: page still served", "Chart unavailable" in page and "mana-ychartpie" in page)
    except Exception as e:
        check("render error: page still served", False, e)
    chart._render_svg = real

    dlg.destroy()
    print("FAILED: " + ", ".join(FAILURES) if FAILURES else "all passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
