#!/usr/bin/env python3

"""Automated check of YHtmlView on the GTK backend.

Needs a graphical session (the widget is shown in a plain Gtk.Window), but
no interaction.  Exercises whichever engine the widget picks:

- WebKitGTK 6.0 (gi namespace WebKit 6.0 installed): the loaded document is
  the sanitized one, page JavaScript does not run, remote images load only
  once allowed (served by a local counting HTTP server), link navigation is
  reported as a YWidgetEvent and never followed, external navigation is
  refused, and with the sanitizer bypassed the engine itself still blocks
  scripts and remote images (CSP).
- Gtk.Label fallback (WebKit 6.0 missing): sanitized text with clickable
  links reported the same way.

Optionally render the demo samples to PNG (WebKit only) for a visual check:

    python3 test/test_htmlview_gtk_headless.py [--snapshots DIR]

Exit code 0 = pass.
"""

import http.server
import importlib.util
import os
import sys
import threading
import time

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ["MUI_BACKEND"] = "gtk"

import gi  # noqa: E402
gi.require_version("Gtk", "4.0")
try:
    gi.require_version("WebKit", "6.0")
    from gi.repository import WebKit  # noqa: E402
except Exception:
    WebKit = None
from gi.repository import GLib, Gtk  # noqa: E402

from manatools.aui.yui import YUI, YUI_ui  # noqa: E402
import manatools.aui.yui_common as yui  # noqa: E402

LINK_PREFIX = "https://mana-htmlview.invalid/link/"
HITS = []
FAILURES = []


class _Counter(http.server.BaseHTTPRequestHandler):
    """Records every request; answers with a 1x1 GIF."""

    def do_GET(self):
        HITS.append(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "image/gif")
        self.end_headers()
        self.wfile.write(b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04"
                         b"\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;")

    def log_message(self, *_args):
        pass


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
    if not cond:
        FAILURES.append(name)


def spin(seconds, until=None):
    """Run the GLib main loop for up to *seconds*, or until until() is true."""
    end = time.time() + seconds
    ctx = GLib.MainContext.default()
    while time.time() < end:
        ctx.iteration(False)
        if until and until():
            return True
        time.sleep(0.01)
    return bool(until and until())


def wait_loaded(web_view, action, seconds=15):
    """Run *action* and wait for the next completed load."""
    state = {}

    def on_load(_view, event):
        if event == WebKit.LoadEvent.FINISHED:
            state["done"] = True
    handler = web_view.connect("load-changed", on_load)
    action()
    ok = spin(seconds, lambda: state)
    web_view.disconnect(handler)
    return ok


def loaded_source(web_view):
    """Bytes WebKit actually loaded as the main document."""
    box = {}
    resource = web_view.get_main_resource()
    if resource is None:
        return ""
    resource.get_data(None, lambda res, task: box.setdefault("data", res.get_data_finish(task)))
    spin(5, lambda: box)
    return bytes(box.get("data") or b"").decode("utf-8", "replace")


def check_webkit(view, dialog, remote):
    wk = view.get_backend_widget()
    settings = wk.get_settings()
    check("webkit: ephemeral session", wk.get_network_session().is_ephemeral())
    check("webkit: javascript off", not settings.get_enable_javascript()
          and not settings.get_enable_javascript_markup())

    html = ('<p>Hello <a href="https://example.com/offer">offer</a></p>'
            '<script>document.title="SANITIZER MISSED"</script>'
            f'<img src="{remote}/remote.gif">')
    check("webkit: document loaded", wait_loaded(wk, lambda: view.setHtml(html)))
    source = loaded_source(wk)
    check("webkit: loaded doc is the sanitized doc", source == view._sanitized().document, source[:200])
    check("webkit: no script in loaded doc", "<script" not in source)
    check("webkit: link rewritten, real url as title", f'href="{LINK_PREFIX}0"' in source
          and 'title="https://example.com/offer"' in source, source)
    check("webkit: page js did not run", wk.get_title() in (None, ""), wk.get_title())
    spin(1)
    check("webkit: remote image not requested", not HITS, HITS)
    check("webkit: remote flagged", view.remoteContentBlocked())

    # Navigation to an opaque link URL must be reported, never followed;
    # load_uri() goes through the same decide-policy path as a click.
    events = []
    post = dialog._post_event
    dialog._post_event = lambda ev: (events.append(ev), post(ev))
    wk.load_uri(f"{LINK_PREFIX}0")
    spin(3, lambda: events)
    dialog._post_event = post
    check("webkit: link reported", view.lastActivatedUrl() == "https://example.com/offer",
          view.lastActivatedUrl())
    check("webkit: YWidgetEvent Activated", bool(events) and events[0].widget() is view
          and events[0].reason() == yui.YEventReason.Activated, events)
    check("webkit: did not navigate", (wk.get_uri() or "about:blank") == "about:blank", wk.get_uri())

    HITS.clear()
    wk.load_uri(f"{remote}/navigate")
    spin(2)
    check("webkit: external navigation refused", "/navigate" not in HITS
          and (wk.get_uri() or "about:blank") == "about:blank", (HITS, wk.get_uri()))
    check("webkit: stale link index ignored", view._activate_link(99) is False)

    check("webkit: reloaded on setAllowRemote", wait_loaded(wk, lambda: view.setAllowRemote(True)))
    spin(3, lambda: HITS)
    check("webkit: remote image loaded when allowed", "/remote.gif" in HITS, HITS)
    view.setAllowRemote(False)

    # Sanitizer bypassed: the engine settings and the CSP alone must hold.
    HITS.clear()
    raw = ('<meta http-equiv="Content-Security-Policy" content="img-src data:">'
           '<script>document.title="JS RAN"</script>'
           f'<img src="{remote}/csp.gif">')
    check("webkit: raw doc loaded", wait_loaded(wk, lambda: wk.load_html(raw, None)))
    spin(1)
    check("webkit: engine blocks page js", wk.get_title() in (None, ""), wk.get_title())
    check("webkit: engine CSP blocks remote image", "/csp.gif" not in HITS, HITS)


def check_label(view, dialog):
    lbl = view._content_widget
    view.setHtml('<h2>T</h2><p>Hi <a href="https://example.com/x">x</a></p><script>alert(1)</script>')
    text = lbl.get_text()
    check("label: sanitized text", "Hi x" in text and "alert" not in text, text)
    check("label: link markup", f'<a href="{LINK_PREFIX}0">' in lbl.get_label())
    events = []
    post = dialog._post_event
    dialog._post_event = lambda ev: (events.append(ev), post(ev))
    lbl.emit("activate-link", f"{LINK_PREFIX}0")
    dialog._post_event = post
    check("label: link reported", view.lastActivatedUrl() == "https://example.com/x"
          and bool(events) and events[0].widget() is view, view.lastActivatedUrl())


def snapshots(view, directory):
    """Render the demo samples to PNG files in *directory*."""
    spec = importlib.util.spec_from_file_location(
        "htmlview_demo", os.path.join(os.path.dirname(__file__), "test_htmlview.py"))
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    os.makedirs(directory, exist_ok=True)
    wk = view.get_backend_widget()
    view.setCidResolver(demo.CID_PARTS.get)
    for name, html, policy in demo.SAMPLES:
        wait_loaded(wk, lambda: view.setHtml(html, policy))
        spin(1)
        box = {}
        wk.get_snapshot(WebKit.SnapshotRegion.FULL_DOCUMENT, WebKit.SnapshotOptions.NONE, None,
                        lambda v, res: box.setdefault("texture", v.get_snapshot_finish(res)))
        spin(10, lambda: box)
        path = os.path.join(directory, f"htmlview_{name.replace(' ', '_').lower()}.png")
        box["texture"].save_to_png(path)
        print(f"snapshot {name}: {path}")


def main():
    snap_dir = None
    if "--snapshots" in sys.argv:
        idx = sys.argv.index("--snapshots")
        snap_dir = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "htmlview_snapshots"

    server = http.server.HTTPServer(("127.0.0.1", 0), _Counter)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    remote = f"http://127.0.0.1:{server.server_address[1]}"

    YUI._instance = None
    YUI._backend = None
    factory = YUI_ui().widgetFactory()
    dialog = factory.createMainDialog()
    vbox = factory.createVBox(dialog)
    view = factory.createHtmlView(vbox)
    backend = view.get_backend_widget()

    window = Gtk.Window()
    window.set_default_size(760, 900)
    window.set_child(backend)
    window.present()
    spin(0.5)

    print(f"engine: {view._engine}")
    check("engine matches availability", view._engine == ("webkit" if WebKit else "label"), view._engine)
    if view._engine == "webkit":
        check_webkit(view, dialog, remote)
    else:
        check_label(view, dialog)

    view.setHelpText("tip")
    check("tooltip", backend.get_tooltip_text() == "tip")
    view.setEnabled(False)
    check("insensitive", not backend.get_sensitive())
    view.setEnabled(True)
    view.setVisible(False)
    check("hidden", not backend.get_visible())
    view.setVisible(True)

    if snap_dir and view._engine == "webkit":
        snapshots(view, snap_dir)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {', '.join(FAILURES)}")
    else:
        print("all checks passed")
    sys.stdout.flush()
    os._exit(1 if FAILURES else 0)


if __name__ == '__main__':
    main()
