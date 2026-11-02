#!/usr/bin/env python3

"""Headless checks of the web backend's WebSocket frame reader.

WebSocketHandler.receive_frame() is driven over a socketpair with hand-built
client frames (masked, as browsers send them):

1. text frames are returned, including 16-bit and 64-bit extended lengths;
2. ping, pong, binary and continuation frames are consumed in full and
   skipped, so the following text frame arrives intact (mask key and
   payload of a skipped frame must not leak into the next header);
3. a ping is answered with a pong;
4. a ping flood is handled iteratively (no recursion) and the connection
   is dropped after 100 consecutive non-text frames;
5. close frames, oversized frames and oversized control frames end the
   connection.

No browser and no dialog needed.
Run directly: python3 test/test_web_ws_frames.py (exit 0 = pass).
"""

import os
import socket
import struct
import sys
import threading

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from manatools.aui.backends.web.server import WebSocketHandler  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
    if not cond:
        FAILURES.append(name)


def frame(opcode, payload=b"", fin=True):
    """Build a masked client frame."""
    head = bytearray([(0x80 if fin else 0) | opcode])
    n = len(payload)
    if n < 126:
        head.append(0x80 | n)
    elif n < 65536:
        head.append(0x80 | 126)
        head += struct.pack(">H", n)
    else:
        head.append(0x80 | 127)
        head += struct.pack(">Q", n)
    key = os.urandom(4)
    return bytes(head) + key + bytes(b ^ key[i % 4] for i, b in enumerate(payload))


def text(msg):
    return frame(0x01, msg.encode("utf-8"))


def ping(payload=b""):
    return frame(0x09, payload)


class Peer:
    """Feed *data* to a fresh handler and collect what it sends back."""

    def __init__(self, data):
        self.srv, self.cli = socket.socketpair()
        self.srv.settimeout(5)
        self.handler = WebSocketHandler(self.srv, None, lambda m: None, lambda: None)
        self.received = bytearray()
        # Separate threads so large inputs and pong replies never fill a
        # socket buffer while the other side is not reading.
        self._sender = threading.Thread(target=self._send, args=(data,), daemon=True)
        self._drainer = threading.Thread(target=self._drain, daemon=True)
        self._sender.start()
        self._drainer.start()

    def _send(self, data):
        try:
            self.cli.sendall(data)
            self.cli.shutdown(socket.SHUT_WR)
        except OSError:
            pass

    def _drain(self):
        try:
            while True:
                chunk = self.cli.recv(65536)
                if not chunk:
                    break
                self.received += chunk
        except OSError:
            pass

    def read(self, count=1):
        out = [self.handler.receive_frame() for _ in range(count)]
        return out[0] if count == 1 else out

    def finish(self):
        """Close the server end and return the bytes the handler sent."""
        self.srv.close()
        self._drainer.join(2)
        self.cli.close()
        return bytes(self.received)


def run_case(data, count=1):
    p = Peer(data)
    r = p.read(count)
    closed = p.handler._closed
    return r, closed, p.finish()


def main():
    # 1. text frames and length encodings
    r, _, _ = run_case(text('{"type":"event"}'))
    check("single text frame", r == '{"type":"event"}', repr(r))

    r, _, _ = run_case(text("one") + text("two"), count=2)
    check("two text frames in sequence", r == ["one", "two"], repr(r))

    msg = "x" * 300
    r, _, _ = run_case(text(msg))
    check("16-bit extended length", r == msg, f"len={len(r or '')}")

    msg = "y" * 70000
    r, _, _ = run_case(text(msg))
    check("64-bit extended length", r == msg, f"len={len(r or '')}")

    msg = "àèìòù €"
    r, _, _ = run_case(text(msg))
    check("utf-8 payload", r == msg, repr(r))

    # 2./3. skipped frames leave the stream in sync; ping gets a pong
    r, _, sent = run_case(ping() + text("after-ping"))
    check("ping then text", r == "after-ping", repr(r))
    check("ping answered with pong", sent.startswith(b"\x8a\x00"), repr(sent[:4]))

    r, _, _ = run_case(ping(b"hello") + text("after-ping-payload"))
    check("ping with payload then text", r == "after-ping-payload", repr(r))

    r, _, _ = run_case(frame(0x0A) + frame(0x0A, b"pong!") + text("after-pong"))
    check("unsolicited pongs then text", r == "after-pong", repr(r))

    r, _, _ = run_case(frame(0x02, os.urandom(1000)) + text("after-binary"))
    check("binary frame then text", r == "after-binary", repr(r))

    r, _, _ = run_case(frame(0x00, b"cont") + text("after-continuation"))
    check("continuation frame then text", r == "after-continuation", repr(r))

    # Random mask keys used to decide whether leftovers happened to resync;
    # repeat so a regression cannot pass by luck.
    bad = 0
    for _ in range(300):
        r, _, _ = run_case(ping() + frame(0x0A) + text("repeat"))
        bad += r != "repeat"
    check("ping/pong then text, 300 random masks", bad == 0, f"{bad} corrupted")

    # 4. ping flood
    r, _, _ = run_case(ping() * 99 + text("under-cap"))
    check("99 pings then text delivered", r == "under-cap", repr(r))

    r, closed, sent = run_case(ping() * 2000 + text("after-flood"))
    check("ping flood drops connection", r is None and closed, f"r={r!r} closed={closed}")
    check("ping flood answered 100 pongs, no more",
          sent == b"\x8a\x00" * 100, f"{len(sent) // 2} pongs")

    # 5. close and oversized frames
    r, closed, _ = run_case(frame(0x08) + text("after-close"))
    check("close frame ends connection", r is None and closed, f"r={r!r} closed={closed}")

    huge = bytes([0x81, 0x80 | 127]) + struct.pack(">Q", WebSocketHandler.MAX_FRAME_SIZE + 1)
    r, closed, _ = run_case(huge)
    check("oversized frame rejected", r is None and closed, f"r={r!r} closed={closed}")

    r, closed, _ = run_case(ping(b"z" * 126) + text("after-big-ping"))
    check("oversized control frame rejected", r is None and closed, f"r={r!r} closed={closed}")

    r, closed, _ = run_case(text("trunc")[:-2])
    check("truncated frame returns None", r is None, repr(r))

    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {', '.join(FAILURES)}")
    else:
        print("all checks passed")
    return 1 if FAILURES else 0


if __name__ == '__main__':
    sys.exit(main())
