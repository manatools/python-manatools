#!/usr/bin/env python3

"""Headless end-to-end check of YChartGauge on the web backend.

Boots a dialog with MUI_BACKEND=web, then talks to the real server:
- the page embeds the dial as inline SVG (track, band arcs, value arc in the
  band color, ticks, target marker, value text) with escaped text and a
  legend row per labelled band;
- POST /event with data.gauge posts an Activated YWidgetEvent; bad payloads,
  disabled gauges and notify(False) post nothing;
- model changes are pushed to the browser as one coalesced update;
- a failing render shows a placeholder instead of breaking the page.

No browser needed.  Run directly: python3 test/test_chartgauge_web_headless.py
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


def chart_html(page, chart_id):
    m = re.search(r'<div id="%s".*?</svg></div>(<ul.*?</ul>)?</div></div>' % re.escape(chart_id), page, re.S)
    return m.group(0) if m else ""


def main():
    YUI._instance = None
    YUI._backend = None
    f = YUI_ui().widgetFactory()
    dlg = f.createMainDialog()
    vbox = f.createVBox(dlg)
    gauge = f.createChartGauge(vbox, "CPU <load>")
    gauge.setBands([(0, 60, None, "OK"), (60, 85, "#E69F00", "Warn <b>"), (85, 100)])
    gauge.setValue(72)
    gauge.setUnit("%")
    gauge.setSubtitle("1 & 5 min")
    gauge.setTarget(90)
    f.createPushButton(vbox, "&OK")

    check("widget class", gauge.widgetClass() == "YChartGauge")

    threading.Thread(target=dlg.open, daemon=True).start()
    for _ in range(50):
        if getattr(getattr(dlg, "_server", None), "port", 0):
            break
        time.sleep(0.1)
    time.sleep(0.5)
    base = f"http://127.0.0.1:{dlg._server.port}"

    html = chart_html(get(base + "/"), gauge.id())
    check("page: chart rendered", 'data-widget-class="YChartGauge"' in html, html[:300])
    check("page: inline svg button", '<svg class="mana-chartgauge-svg"' in html
          and 'data-gauge="1"' in html and 'role="button"' in html)
    check("page: track", html.count('class="mana-chartgauge-track"') == 1)
    check("page: band arcs", html.count('class="mana-chartgauge-band"') == 3)
    check("page: value arc in band color", re.search(r'class="mana-chartgauge-value" fill="#e69f00"', html))
    check("page: ticks", html.count('class="mana-chartgauge-ticklabel"') == 6
          and ">100</text>" in html)
    check("page: target", html.count('class="mana-chartgauge-target"') == 1)
    check("page: no needle by default", "mana-chartgauge-needle" not in html)
    check("page: value text", ">72%</text>" in html)
    check("page: subtitle escaped", ">1 &amp; 5 min</text>" in html)
    check("page: title escaped", "CPU &lt;load&gt;" in html and "<load>" not in html)
    check("page: legend labelled bands", html.count('class="mana-chartgauge-legend-row"') == 2
          and "Warn &lt;b&gt;" in html and "<b>" not in html)
    check("page: no inline handlers", not re.search(r"\son[a-z]+=", html))

    sent = []
    orig_broadcast = dlg._broadcast
    dlg._broadcast = lambda msg: (sent.append(msg), orig_broadcast(msg))

    # -- click ---------------------------------------------------------------
    post_event(base, {"type": "event", "widget_id": gauge.id(), "reason": "Activated",
                      "data": {"gauge": True}})
    ev = dlg.waitForEvent(2000)
    check("click: event posted", ev.eventType() == yui.YEventType.WidgetEvent
          and ev.widget() is gauge and ev.reason() == yui.YEventReason.Activated,
          (ev.eventType(), ev.widget()))

    for bad in (1, "true", None, [True], {"x": 1}, False):
        post_event(base, {"type": "event", "widget_id": gauge.id(), "reason": "Activated",
                          "data": {"gauge": bad}})
    ev = dlg.waitForEvent(500)
    check("click: bad payloads ignored", ev.eventType() == yui.YEventType.TimeoutEvent, ev.eventType())

    gauge.setEnabled(False)
    post_event(base, {"type": "event", "widget_id": gauge.id(), "data": {"gauge": True}})
    ev = dlg.waitForEvent(500)
    check("click: disabled ignored", ev.eventType() == yui.YEventType.TimeoutEvent)
    gauge.setEnabled(True)

    gauge.setNotify(False)
    post_event(base, {"type": "event", "widget_id": gauge.id(), "data": {"gauge": True}})
    ev = dlg.waitForEvent(500)
    check("click: notify off, no event", ev.eventType() == yui.YEventType.TimeoutEvent)
    gauge.setNotify(True)

    # -- live updates --------------------------------------------------------
    time.sleep(0.3)
    sent.clear()
    gauge.setValue(95)
    gauge.setShowNeedle(True)
    gauge.setSweepAngle(180)
    gauge.setLegendPosition(YChartLegendPosition.Bottom)
    time.sleep(0.4)
    updates = [u for m in sent if m.get("type") == "update" for u in m.get("updates", [])]
    check("update: coalesced to one", len(updates) == 1, len(updates))
    upd = updates[0]["html"] if updates else ""
    check("update: new value", ">95%</text>" in upd)
    check("update: needle", "mana-chartgauge-needle" in upd)
    check("update: band color follows value", re.search(r'class="mana-chartgauge-value" fill="#d55e00"', upd))
    check("update: legend bottom", "mana-chartgauge-legend-bottom" in upd)

    sent.clear()
    gauge.setLegendPosition(YChartLegendPosition.Hidden)
    gauge.setShowTicks(False)
    gauge.setShowValue(False)
    gauge.setTarget(None)
    time.sleep(0.3)
    upd = json.dumps(sent)
    check("hidden parts", "mana-chartgauge-legend\\\"" not in upd and "ticklabel" not in upd
          and "valuetext" not in upd and "mana-chartgauge-target" not in upd, upd[:400])

    try:
        gauge.addBand(0, 1, '#000" onload="x')
        check("color: injection rejected", False)
    except ValueError:
        check("color: injection rejected", True)

    # -- extremes stay finite ----------------------------------------------------
    gauge.setRange(-1e300, 1e300)
    gauge.setValue(1e300)
    gauge.setShowTicks(True)
    svg = gauge._render_svg()
    check("extreme range renders", not re.search(r"\b(nan|inf)\b", svg, re.I)
          and ">1e+300</text>" in svg.replace("1e+300%", "1e+300"), re.findall(r">[^<]*</text>", svg))
    gauge.setRange(0, 100)

    # -- a failing chart must not break the page --------------------------------
    real = gauge._render_svg
    gauge._render_svg = lambda: 1 / 0
    try:
        page = get(base + "/")
        check("render error: page still served", "Chart unavailable" in page and "mana-ychartgauge" in page)
    except Exception as e:
        check("render error: page still served", False, e)
    gauge._render_svg = real

    dlg.destroy()
    print("FAILED: " + ", ".join(FAILURES) if FAILURES else "all passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
