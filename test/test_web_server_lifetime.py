#!/usr/bin/env python3

"""Headless checks of the web backend's process-wide server.

One server serves every dialog, so the URL the browser was given keeps working
while dialogs come and go:

1. a popup opened before the main dialog, then the main dialog: same port,
   the browser gets hide_modal then reload (never shutdown), and GET / shows
   the main dialog;
2. main dialogs one after another: idle, then reload, same port;
3. stacked main dialogs: closing the top one shows the one below;
4. events posted after the switch reach the new main dialog;
5. YUI.ui().shutdown() sends shutdown once and releases the port.

A raw WebSocket client stands in for the browser.  No browser needed.
Run directly: python3 test/test_web_server_lifetime.py (exit 0 = pass).
"""

import base64
import json
import os
import socket
import struct
import sys
import threading
import time
import urllib.request

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ["MUI_BACKEND"] = "web"
os.environ.pop("MUI_WEB_PORT", None)

from manatools.aui.yui import YUI, YUI_ui  # noqa: E402
import manatools.aui.yui_common as yui  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
    if not cond:
        FAILURES.append(name)


class WSClient:
    """Minimal RFC 6455 client: sends masked text frames, records messages."""

    def __init__(self, port):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=5)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((
            "GET /ws HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{port}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
            f"Origin: http://127.0.0.1:{port}\r\n\r\n"
        ).encode())
        head = b""
        while b"\r\n\r\n" not in head:
            head += self.sock.recv(1)
        assert b" 101 " in head.split(b"\r\n", 1)[0], head
        self.sock.settimeout(None)
        self.messages = []
        self._cond = threading.Condition()
        threading.Thread(target=self._reader, daemon=True).start()

    def _recv(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError
            buf += chunk
        return buf

    def _reader(self):
        try:
            while True:
                b0, b1 = self._recv(2)
                length = b1 & 0x7F
                if length == 126:
                    length = struct.unpack(">H", self._recv(2))[0]
                elif length == 127:
                    length = struct.unpack(">Q", self._recv(8))[0]
                payload = self._recv(length)
                if b0 & 0x0F == 0x08:
                    break
                with self._cond:
                    self.messages.append(json.loads(payload))
                    self._cond.notify_all()
        except Exception:
            pass

    def send(self, obj):
        payload = json.dumps(obj).encode()
        mask = os.urandom(4)
        header = bytes([0x81])
        if len(payload) < 126:
            header += bytes([0x80 | len(payload)])
        else:
            header += bytes([0x80 | 126]) + struct.pack(">H", len(payload))
        self.sock.sendall(header + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def types(self):
        with self._cond:
            return [m.get("type") for m in self.messages]

    def wait_for(self, msg_type, count=1, timeout=3.0):
        deadline = time.monotonic() + timeout
        with self._cond:
            while self.types_locked().count(msg_type) < count:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._cond.wait(remaining)
        return True

    def types_locked(self):
        return [m.get("type") for m in self.messages]

    def clear(self):
        with self._cond:
            self.messages.clear()


def get_page(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as r:
        return r.read().decode()


def post_event(port, payload):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/event", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status


def main():
    YUI._instance = None
    YUI._backend = None
    f = YUI_ui().widgetFactory()

    # -- 1. popup before main ---------------------------------------------
    pop = f.createPopupDialog()
    f.createLabel(pop, "Passphrase?")
    pop.open()
    port = pop._server.port
    page = get_page(port)
    check("popup first: page is an empty shell", "Passphrase?" not in page and 'id="mana-app"' in page)
    ws = WSClient(port)
    ws.send({"type": "ready"})
    check("popup first: ready replays show_modal", ws.wait_for("show_modal"), ws.types())

    pop.destroy()
    main_dlg = f.createMainDialog()
    vbox = f.createVBox(main_dlg)
    f.createLabel(vbox, "Main window")
    button = f.createPushButton(vbox, "Go")
    main_dlg.open()
    check("popup first: same port", main_dlg._server.port == port, (main_dlg._server.port, port))
    check("popup first: reload received", ws.wait_for("reload"), ws.types())
    types = ws.types()
    check("popup first: hide_modal before reload",
          "hide_modal" in types and types.index("hide_modal") < types.index("reload"), types)
    check("popup first: no shutdown", "shutdown" not in types, types)
    check("popup first: GET / shows main", "Main window" in get_page(port))

    # -- 4. events after the switch ---------------------------------------
    post_event(port, {"type": "event", "widget_id": button.id(), "reason": "Activated", "data": {}})
    ev = main_dlg.waitForEvent(2000)
    check("events: reach the main dialog", ev.eventType() == yui.YEventType.WidgetEvent and ev.widget() is button,
          (ev.eventType(), getattr(ev, "widget", lambda: None)()))

    # -- 2. sequential main dialogs ---------------------------------------
    ws.clear()
    main_dlg.destroy()
    check("sequential: idle on last main closed", ws.wait_for("idle"), ws.types())
    check("sequential: server still serves", "Main window" not in get_page(port))
    dlg_b = f.createMainDialog()
    f.createLabel(dlg_b, "Dialog B")
    dlg_b.open()
    check("sequential: reload on next main", ws.wait_for("reload"), ws.types())
    check("sequential: same port", dlg_b._server.port == port)
    check("sequential: GET / shows B", "Dialog B" in get_page(port))
    check("sequential: no shutdown", "shutdown" not in ws.types(), ws.types())

    # -- 3. stacked main dialogs ------------------------------------------
    ws.clear()
    dlg_c = f.createMainDialog()
    f.createLabel(dlg_c, "Dialog C")
    dlg_c.open()
    check("stacked: GET / shows C", "Dialog C" in get_page(port))
    dlg_c.destroy()
    check("stacked: two reloads", ws.wait_for("reload", count=2), ws.types())
    page = get_page(port)
    check("stacked: GET / shows B again", "Dialog B" in page and "Dialog C" not in page)

    # -- 5. shutdown -------------------------------------------------------
    ws.clear()
    YUI.ui().shutdown()
    check("shutdown: sent", ws.wait_for("shutdown"), ws.types())
    YUI.ui().shutdown()
    time.sleep(0.2)
    check("shutdown: sent once", ws.types().count("shutdown") == 1, ws.types())
    try:
        socket.create_connection(("127.0.0.1", port), timeout=1).close()
        check("shutdown: port released", False)
    except OSError:
        check("shutdown: port released", True)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {', '.join(FAILURES)}")
    else:
        print("all checks passed")
    sys.stdout.flush()
    os._exit(1 if FAILURES else 0)


if __name__ == '__main__':
    main()
