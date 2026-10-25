#!/usr/bin/env python3

"""Headless checks of web-backend widget APIs brought in line with Qt.

Covers the "Tier A" gaps: selection API of YSelectionBox and YTree, YRichText
state, YImage zero size, YSpacing getters, YProgressBar properties, YAlignment,
YFrame, YReplacePoint, YPaned and YDumbTab container behaviour, and
YDialog.setVisible.  It also boots the real server to check that a child added
after open() is pushed to the browser and receives events, and that a
selection-box click is handled.

No browser needed.  Run directly: python3 test/test_web_widgets_headless.py
(exit 0 = pass).
"""

import json
import os
import sys
import threading
import time
import urllib.request

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ["MUI_BACKEND"] = "web"

from manatools.aui.yui import YUI, YUI_ui  # noqa: E402
import manatools.aui.yui_common as yui  # noqa: E402

FAILURES = []
H, V = yui.YUIDimension.YD_HORIZ, yui.YUIDimension.YD_VERT


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
    if not cond:
        FAILURES.append(name)


def post_event(base, payload):
    req = urllib.request.Request(base + "/event", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status


def main():
    YUI._instance = None
    YUI._backend = None
    f = YUI_ui().widgetFactory()
    dlg = f.createMainDialog()
    vbox = f.createVBox(dlg)

    # -- YSelectionBox -----------------------------------------------------
    sel = f.createSelectionBox(vbox, "Pick")
    items = [yui.YItem(x) for x in ("a", "b", "c")]
    for it in items:
        sel.addItem(it)
    check("selbox: label", sel.label() == "Pick")
    sel.selectItem(items[0])
    sel.selectItem(items[1])
    check("selbox: single selection replaces", sel.selectedItems() == [items[1]]
          and not items[0].selected() and items[1].selected())
    sel.setMultiSelection(True)
    check("selbox: multiSelection", sel.multiSelection())
    sel.selectItem(items[2])
    check("selbox: multi selection adds", sel.selectedItems() == [items[1], items[2]])
    sel.selectItem(items[1], False)
    check("selbox: deselect", sel.selectedItems() == [items[2]] and not items[1].selected())
    sel.selectItem(items[0])
    sel.setMultiSelection(False)
    check("selbox: leaving multi keeps first", sel.selectedItems() == [items[2]] and not items[0].selected(),
          [i.label() for i in sel.selectedItems()])
    sel.setLabel("Pick one")
    check("selbox: setLabel renders", "Pick one" in sel.render())

    # -- YTree ---------------------------------------------------------------
    tree = f.createTree(vbox, "Tree")
    root = yui.YTreeItem("root")
    kid = yui.YTreeItem("kid", root)
    tree.addItem(root)
    tree.selectItem(kid)
    check("tree: selectItem", tree.currentItem() is kid and kid.selected())
    tree.selectItem(root)
    check("tree: single selection replaces", tree.selectedItems() == [root] and not kid.selected())
    check("tree: immediateMode property", tree.setProperty("immediateMode", True)
          and tree.getProperty("immediateMode") is True)
    calls = []
    orig = dlg._schedule_update
    dlg._schedule_update = lambda w: calls.append(w)
    tree.render()
    tree.render()
    dlg._schedule_update = orig
    check("tree: render does not schedule itself", not calls, calls)

    # -- YRichText -----------------------------------------------------------
    rt = f.createRichText(vbox, "<b>x</b>")
    check("richtext: value", rt.value() == "<b>x</b>")
    rt.setPlainTextMode(True)
    check("richtext: plain mode escapes", rt.plainTextMode() and "&lt;b&gt;" in rt.render())
    rt.setAutoScrollDown(True)
    check("richtext: autoscroll attr", rt.autoScrollDown() and 'data-autoscroll="1"' in rt.render())
    target, html, action = rt.render_update()
    check("richtext: attribute change forces full replace", action == "replace" and html.startswith("<div"))
    check("richtext: content change stays partial", rt.render_update()[2] == "html")
    rt.setVisible(False)
    check("richtext: hidden", rt.render_update()[2] == "replace" and "display: none" in rt.render())
    rt.setVisible(True)

    # -- YImage / YSpacing / YProgressBar -----------------------------------------
    img = f.createImage(vbox, "")
    img.setZeroSize(H, True)
    check("image: zero size", img.hasZeroSize(H) and not img.hasZeroSize(V) and "min-width: 0" in img.render())
    img.setStretchable(V, True)
    check("image: setStretchable", img.stretchable(V))
    sp = f.createVSpacing(vbox, 12)
    check("spacing: getters", sp.dimension() == V and sp.size() == 12 and sp.sizeDim(V) == 12 and sp.sizeDim(H) == 0,
          (sp.dimension(), sp.size()))
    pb = f.createProgressBar(vbox, "Load", 200)
    check("progress: setProperty value", pb.setProperty("value", 50) and pb.getProperty("value") == 50)
    check("progress: maxValue property", pb.getProperty("maxValue") == 200)
    check("progress: propertySet", pb.propertySet() is not None)
    check("progress: stretches horizontally only", pb.stretchable(H) and not pb.stretchable(V))

    # -- containers ----------------------------------------------------------
    al = f.createHCenter(vbox)
    f.createLabel(al, "c")
    check("alignment: center stretches", al.stretchable(H) and not al.stretchable(V))
    al.setAlignment(yui.YAlignmentType.YAlignBegin, yui.YAlignmentType.YAlignCenter)
    check("alignment: setAlignment", not al.stretchable(H) and al.stretchable(V)
          and "justify-content: flex-start" in al.render())
    fr = f.createFrame(vbox, "Frame")
    inner = f.createRichText(fr, "x")
    check("frame: stretch follows child", fr.stretchable(V) == inner.stretchable(V))
    check("frame: propertySet", fr.propertySet() is not None)
    rp = f.createReplacePoint(vbox)
    check("replacepoint: empty does not stretch", not rp.stretchable(H))
    paned = f.createPaned(vbox, H)
    for n in range(3):
        f.createLabel(paned, f"p{n}")
    check("paned: two children max", paned.childrenCount() == 2)
    tabs = f.createDumbTab(vbox)
    tabs.addItem(yui.YItem("one"))
    f.createLabel(tabs, "content")
    try:
        f.createLabel(tabs, "second")
        check("dumbtab: one child only", False)
    except yui.YUIInvalidWidgetException:
        check("dumbtab: one child only", True)
    tabs.deleteAllItems()
    check("dumbtab: deleteAllItems", tabs.itemsCount() == 0)

    # -- live server: dialog visibility, late children, selection events --------
    late_box = f.createVBox(vbox)
    threading.Thread(target=dlg.open, daemon=True).start()
    for _ in range(50):
        if getattr(getattr(dlg, "_server", None), "port", 0):
            break
        time.sleep(0.1)
    time.sleep(0.5)
    base = f"http://127.0.0.1:{dlg._server.port}"

    sent = []
    orig_broadcast = dlg._broadcast
    dlg._broadcast = lambda msg: (sent.append(msg), orig_broadcast(msg))

    late = f.createPushButton(late_box, "Late button")
    time.sleep(0.3)
    check("late child: pushed to browser", any("Late button" in json.dumps(m) for m in sent))
    post_event(base, {"type": "event", "widget_id": late.id(), "reason": "Activated", "data": {}})
    ev = dlg.waitForEvent(2000)
    check("late child: event routed", ev.eventType() == yui.YEventType.WidgetEvent and ev.widget() is late,
          (ev.eventType(), ev.widget()))

    sel.setMultiSelection(True)
    post_event(base, {"type": "event", "widget_id": sel.id(), "reason": "SelectionChanged",
                      "data": {"selectedIndex": [0, 2]}})
    ev = dlg.waitForEvent(2000)
    check("selbox click: event posted", ev.eventType() == yui.YEventType.WidgetEvent and ev.widget() is sel)
    check("selbox click: selection applied", [i.label() for i in sel.selectedItems()] == ["a", "c"]
          and items[0].selected() and not items[1].selected())

    sent.clear()
    dlg.setVisible(False)
    check("dialog: hide broadcast", any(u.get("action") == "attr" and u.get("attr") == "hidden" and u.get("value")
                                        for m in sent for u in m.get("updates", [])), sent)
    check("dialog: hidden in render", f'<div hidden id="{dlg.id()}"' in dlg.render())
    dlg.setVisible(True)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {', '.join(FAILURES)}")
    else:
        print("all checks passed")
    sys.stdout.flush()
    os._exit(1 if FAILURES else 0)


if __name__ == '__main__':
    main()
