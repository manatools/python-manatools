#!/usr/bin/env python3

"""Headless end-to-end check of YHtmlView on the web backend.

Boots a dialog with MUI_BACKEND=web, then talks to the real server:
- the dialog page embeds the view as <iframe sandbox="">, not inline HTML;
- /htmlview/<token> serves the sanitized document with its own strict CSP;
- /htmlview/<token>/link/<n> answers 204 and posts a YWidgetEvent;
- foreign Host, foreign Origin, non-frame Sec-Fetch-Dest and stale tokens
  are refused;
- setHtml()/setAllowRemote() rotate the token and update the CSP.

No browser needed.  Run directly: python3 test/test_htmlview_web_headless.py
(exit 0 = pass).
"""

import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ["MUI_BACKEND"] = "web"

from manatools.aui.yui import YUI, YUI_ui  # noqa: E402
import manatools.aui.yui_common as yui  # noqa: E402

HOSTILE = ('<p>Hello <a href="https://example.com/offer">offer</a> '
           '<a href="javascript:alert(1)">js</a></p>'
           '<script>alert(1)</script><img src="https://track.example/p.gif">'
           '<p onclick="x()">click</p>')

FAILURES = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
    if not cond:
        FAILURES.append(name)


def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.headers, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.headers, ""


def frame_src(base, html_view_id):
    _, _, page = get(base)
    m = re.search(r'<div id="%s"[^>]*>\s*<iframe[^>]*src="(/htmlview/[^"]+)"' % re.escape(html_view_id), page)
    return page, (m.group(1) if m else None)


def main():
    YUI._instance = None
    YUI._backend = None
    factory = YUI_ui().widgetFactory()
    dialog = factory.createMainDialog()
    vbox = factory.createVBox(dialog)
    view = factory.createHtmlView(vbox, HOSTILE)
    factory.createPushButton(vbox, "&OK")

    threading.Thread(target=dialog.open, daemon=True).start()
    for _ in range(50):
        if getattr(getattr(dialog, "_server", None), "port", 0):
            break
        time.sleep(0.1)
    time.sleep(0.5)
    base = f"http://127.0.0.1:{dialog._server.port}"

    page, src = frame_src(base + "/", view.id())
    check("page: widget class", view.widgetClass() == "YHtmlView")
    check("page: sandboxed iframe", src is not None and 'sandbox=""' in page, page[:400])
    check("page: content not inlined", "offer" not in page and "track.example" not in page)

    frame_headers = {"Sec-Fetch-Dest": "iframe"}
    status, headers, doc = get(base + src, frame_headers)
    csp = headers.get("Content-Security-Policy", "")
    check("doc: 200", status == 200, status)
    check("doc: CSP sandbox, no script", "sandbox" in csp and "script-src" not in csp
          and "default-src 'none'" in csp, csp)
    check("doc: CSP blocks remote images", "img-src data:;" in csp, csp)
    check("doc: frameable by self only", headers.get("X-Frame-Options") == "SAMEORIGIN"
          and "frame-ancestors 'self'" in csp, headers.get("X-Frame-Options"))
    check("doc: nosniff + no-referrer", headers.get("X-Content-Type-Options") == "nosniff"
          and headers.get("Referrer-Policy") == "no-referrer")
    check("doc: no-store", headers.get("Cache-Control") == "no-store")
    check("doc: sanitized", "<script" not in doc and "onclick" not in doc
          and "track.example" not in doc and "javascript:" not in doc, doc)
    links = re.findall(r'href="(/htmlview/[^"]+/link/\d+)"', doc)
    check("doc: one opaque link", len(links) == 1 and links[0].startswith(src + "/link/"), links)
    check("model: remote blocked flag", view.remoteContentBlocked())

    # refusals
    check("refuse: foreign Host", get(base + src, {"Host": "evil.example:80", **frame_headers})[0] == 403)
    check("refuse: foreign Origin", get(base + src, {"Origin": "http://evil.example", **frame_headers})[0] == 403)
    check("refuse: image fetch", get(base + src, {"Sec-Fetch-Dest": "image"})[0] == 403)
    check("refuse: unknown token", get(base + "/htmlview/" + "A" * 32, frame_headers)[0] == 404)
    check("refuse: bad path", get(base + "/htmlview/../server.py", frame_headers)[0] == 404)
    check("refuse: link out of range", get(base + src + "/link/99", frame_headers)[0] == 204
          and view.lastActivatedUrl() is None)

    # link activation
    status, headers, _ = get(base + links[0], frame_headers)
    check("link: 204", status == 204, status)
    check("link: frameable headers on 204", headers.get("X-Frame-Options") == "SAMEORIGIN")
    ev = dialog.waitForEvent(2000)
    check("link: YWidgetEvent posted", ev.eventType() == yui.YEventType.WidgetEvent
          and ev.widget() is view and ev.reason() == yui.YEventReason.Activated,
          (ev.eventType(), ev.widget()))
    check("link: original url reported", view.lastActivatedUrl() == "https://example.com/offer",
          view.lastActivatedUrl())

    # content change rotates the token; old document and links die
    view.setHtml('<p><a href="https://second.example">second</a></p>')
    time.sleep(0.3)
    _, src2 = frame_src(base + "/", view.id())
    check("rotate: new token", src2 is not None and src2 != src, (src, src2))
    check("rotate: old doc gone", get(base + src, frame_headers)[0] == 404)
    check("rotate: old link gone", get(base + links[0], frame_headers)[0] == 404)

    view.setAllowRemote(True)
    _, src3 = frame_src(base + "/", view.id())
    _, headers, doc = get(base + src3, frame_headers)
    check("remote: CSP allows images", "img-src data: http: https:" in headers.get("Content-Security-Policy", ""))
    check("remote: content updated", "second.example" in doc)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {', '.join(FAILURES)}")
        sys.stdout.flush()
        os._exit(1)
    print("all checks passed")
    sys.stdout.flush()
    os._exit(0)


if __name__ == '__main__':
    main()
