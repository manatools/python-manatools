# -*- coding: utf-8 -*-
"""
HTTP and WebSocket server for the web backend.

License: LGPLv2+

Author:  Matteo Pasotti <xquiet@coriolite.com>

This module provides a simple HTTP server that serves the dialog HTML
and handles WebSocket connections for real-time event communication.
"""

import http.server
import socketserver
import threading
import json
import os
import re
import glob as _glob
import logging
import hashlib
import base64
import struct
import socket
from typing import Optional, TYPE_CHECKING, Callable
from urllib.parse import urlparse, parse_qs
from importlib.resources import files

if TYPE_CHECKING:
    from .dialogweb import YDialogWeb

logger = logging.getLogger("manatools.aui.web.server")


class WebSocketHandler:
    """
    Simple WebSocket handler implementing RFC 6455.

    This is a minimal implementation that handles text frames only.
    """

    GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(
        self,
        request,
        client_address,
        on_message: Callable[[str], None],
        on_close: Callable[[], None],
    ):
        self.request = request
        self.client_address = client_address
        self.on_message = on_message
        self.on_close = on_close
        self._closed = False
        self._lock = threading.Lock()

    @classmethod
    def handshake(cls, request_handler) -> Optional["WebSocketHandler"]:
        """Perform WebSocket handshake. Returns WebSocketHandler on success."""
        try:
            key = request_handler.headers.get("Sec-WebSocket-Key")
            if not key:
                return None

            accept = hashlib.sha1((key + cls.GUID).encode()).digest()
            accept_key = base64.b64encode(accept).decode()

            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept_key}\r\n"
                "\r\n"
            )
            request_handler.wfile.write(response.encode())
            request_handler.wfile.flush()

            return cls(
                request_handler.request,
                request_handler.client_address,
                lambda msg: None,  # Placeholder, set by caller
                lambda: None,
            )
        except Exception as e:
            logger.exception("WebSocket handshake failed: %s", e)
            return None

    def receive_frame(self) -> Optional[str]:
        """Receive a WebSocket frame and return the text payload."""
        try:
            header = self.request.recv(2)
            if len(header) < 2:
                return None

            fin = (header[0] >> 7) & 1
            opcode = header[0] & 0x0F
            masked = (header[1] >> 7) & 1
            payload_len = header[1] & 0x7F

            if opcode == 0x08:  # Close frame
                self._closed = True
                return None

            if opcode == 0x09:  # Ping
                self._send_pong()
                return self.receive_frame()

            if opcode != 0x01:  # Not a text frame
                return self.receive_frame()

            if payload_len == 126:
                ext = self.request.recv(2)
                payload_len = struct.unpack(">H", ext)[0]
            elif payload_len == 127:
                ext = self.request.recv(8)
                payload_len = struct.unpack(">Q", ext)[0]

            mask_key = self.request.recv(4) if masked else b""
            payload = self.request.recv(payload_len)

            if masked:
                payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))

            return payload.decode("utf-8")
        except Exception as e:
            if not self._closed:
                logger.debug("WebSocket receive error: %s", e)
            return None

    def send(self, message: str):
        """Send a text message through the WebSocket."""
        with self._lock:
            if self._closed:
                return
            try:
                payload = message.encode("utf-8")
                length = len(payload)

                frame = bytearray()
                frame.append(0x81)  # FIN + text opcode

                if length < 126:
                    frame.append(length)
                elif length < 65536:
                    frame.append(126)
                    frame.extend(struct.pack(">H", length))
                else:
                    frame.append(127)
                    frame.extend(struct.pack(">Q", length))

                frame.extend(payload)
                self.request.sendall(bytes(frame))
            except Exception as e:
                logger.debug("WebSocket send error: %s", e)
                self._closed = True

    def _send_pong(self):
        """Send a pong frame."""
        with self._lock:
            try:
                self.request.sendall(bytes([0x8A, 0x00]))
            except Exception:
                pass

    def close(self):
        """Close the WebSocket connection."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            try:
                self.request.sendall(bytes([0x88, 0x00]))
            except Exception:
                pass

    def run(self):
        """Main loop to receive and process messages."""
        try:
            while not self._closed:
                message = self.receive_frame()
                if message is None:
                    break
                try:
                    self.on_message(message)
                except Exception as e:
                    logger.exception("Error handling WebSocket message: %s", e)
        finally:
            self._closed = True
            try:
                self.on_close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Page builder
# ---------------------------------------------------------------------------

class PageBuilder:
    """
    Builds the full HTML page by loading ``templates/base.html`` from the
    package and substituting the three runtime slots:

    * ``{{ title }}``       - window / tab title
    * ``{{ app_name }}``    - navbar brand text
    * ``{{ dialog_html }}`` - rendered widget tree

    The template is read from disk exactly once (class-level cache) so
    repeated requests pay no I/O cost.
    """

    _template: Optional[str] = None
    _template_lock = threading.Lock()

    @classmethod
    def _load_template(cls) -> str:
        if cls._template is None:
            with cls._template_lock:
                # Double-checked locking: another thread may have loaded it
                # while we were waiting on the lock.
                if cls._template is None:
                    cls._template = (
                        files("manatools.aui.backends.web")
                        .joinpath("templates/base.html")
                        .read_text(encoding="utf-8")
                    )
        return cls._template

    @classmethod
    def build(cls, *, title: str, app_name: str, dialog_html: str) -> str:
        """Return the complete HTML document as a string."""
        return (
            cls._load_template()
            .replace("{{ title }}", title)
            .replace("{{ app_name }}", app_name)
            .replace("{{ dialog_html }}", dialog_html)
        )


# ---------------------------------------------------------------------------
# XDG icon lookup
# ---------------------------------------------------------------------------

_ICON_NAME_RE = re.compile(r'^[a-zA-Z0-9_\-]+$')

_ICON_SEARCH_DIRS = [
    "/usr/share/icons/hicolor",
    "/usr/share/icons/breeze",
    "/usr/share/icons/Adwaita",
    "/usr/share/icons/breeze-dark",
    "/usr/local/share/icons/hicolor",
]

_ICON_SIZES = ["22x22", "24x24", "22", "24", "scalable", "16x16", "32x32", "48x48"]
_ICON_CATEGORIES = ["actions", "apps", "emblems", "status", "places", "mimetypes"]
_ICON_EXTENSIONS = [(".svg", "image/svg+xml"), (".png", "image/png")]


def _find_icon_file(icon_name: str) -> Optional[tuple]:
    """Return (filepath, mimetype) for a named XDG icon, or None if not found.

    Searches standard system icon theme directories for the given icon name.
    The icon_name must contain only [a-zA-Z0-9_-] characters (validated by caller).
    Prefers SVG (scalable) over PNG; prefers 22px over other sizes.
    """
    # Structured search: known roots × sizes × categories
    for root in _ICON_SEARCH_DIRS:
        if not os.path.isdir(root):
            continue
        for size in _ICON_SIZES:
            for category in _ICON_CATEGORIES:
                for ext, mime in _ICON_EXTENSIONS:
                    path = os.path.join(root, size, category, icon_name + ext)
                    if os.path.isfile(path):
                        return path, mime
                # Also try "scalable" subfolder under size (some themes)
                for ext, mime in _ICON_EXTENSIONS:
                    path = os.path.join(root, "scalable", category, icon_name + ext)
                    if os.path.isfile(path):
                        return path, mime

    # Broader glob over all installed icon themes
    for root in ["/usr/share/icons", "/usr/local/share/icons",
                 os.path.expanduser("~/.local/share/icons")]:
        if not os.path.isdir(root):
            continue
        for ext, mime in _ICON_EXTENSIONS:
            matches = _glob.glob(
                os.path.join(root, "**", icon_name + ext), recursive=True
            )
            if matches:
                return matches[0], mime

    # Fallback: /usr/share/pixmaps
    for ext, mime in _ICON_EXTENSIONS:
        path = f"/usr/share/pixmaps/{icon_name}{ext}"
        if os.path.isfile(path):
            return path, mime

    return None


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

class ManaToolsRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for ManaTools web backend."""

    # Injected by WebServer via a per-request subclass
    dialog: Optional["YDialogWeb"] = None

    def log_message(self, format, *args):
        logger.debug(format, *args)

    def handle_one_request(self):
        """Override to suppress flush errors after a WebSocket upgrade."""
        try:
            super().handle_one_request()
        except Exception:
            # After a WebSocket upgrade the underlying socket is owned by
            # WebSocketHandler.run().  BaseHTTPRequestHandler tries to flush
            # wfile when handle_one_request() returns, which raises on Windows
            # because the socket is in raw mode.  Swallow silently here.
            pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._serve_main_page()
        elif path == "/ws":
            self._handle_websocket()
        elif path.startswith("/static/"):
            self._serve_static(path[len("/static/"):])
        elif path.startswith("/icon/"):
            self._serve_icon(path[len("/icon/"):])
        elif path == "/events":
            self._serve_sse()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        if urlparse(self.path).path == "/event":
            self._handle_event_post()
        else:
            self.send_error(404, "Not Found")

    # ------------------------------------------------------------------
    # Page serving
    # ------------------------------------------------------------------

    def _resolve_title(self) -> str:
        """Return the application title, falling back to 'ManaTools'."""
        try:
            from ...yui import YUI
            app = YUI.application()
            if app:
                return app.applicationTitle() or "ManaTools"
        except Exception:
            pass
        return "ManaTools"

    def _serve_main_page(self):
        if not self.dialog:
            self.send_error(500, "No dialog available")
            return
        try:
            from .commonweb import set_initial_render
            title = self._resolve_title()
            set_initial_render(True)
            try:
                dialog_html = self.dialog.render()
            finally:
                set_initial_render(False)
            html = PageBuilder.build(
                title=title,
                app_name=title,
                dialog_html=dialog_html,
            )
            encoded = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        except Exception as e:
            logger.exception("Error serving main page: %s", e)
            self.send_error(500, str(e))

    # ------------------------------------------------------------------
    # Static files
    # ------------------------------------------------------------------

    _CONTENT_TYPES = {
        ".css":   "text/css",
        ".js":    "application/javascript",
        ".map":   "application/json",          # source maps shipped with Bootstrap
        ".png":   "image/png",
        ".svg":   "image/svg+xml",
        ".ico":   "image/x-icon",
        ".woff2": "font/woff2",
        ".woff":  "font/woff",
        ".ttf":   "font/ttf",
    }

    def _serve_static(self, filename: str):
        # Resolve both roots to absolute real paths so that symlinks and any
        # OS-level normalisation are accounted for before the containment check.
        static_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), "static"))
        filepath   = os.path.realpath(os.path.join(static_dir, filename))

        # Reject anything that escapes the static root (path traversal guard).
        # The trailing sep ensures "/static/css" cannot escape via "/static/css../".
        if not filepath.startswith(static_dir + os.sep):
            self.send_error(403, "Forbidden")
            return

        if not os.path.isfile(filepath):
            self.send_error(404, "Not Found")
            return

        ext = os.path.splitext(filename)[1].lower()
        content_type = self._CONTENT_TYPES.get(ext, "application/octet-stream")

        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            logger.debug("Client disconnected while serving static file %s", filename)
        except Exception as e:
            logger.exception("Error serving static file %s: %s", filename, e)
            self.send_error(500, str(e))

    # ------------------------------------------------------------------
    # Icon serving
    # ------------------------------------------------------------------

    def _serve_icon(self, icon_name: str):
        """Serve a system icon by its XDG icon name.

        Only names matching [a-zA-Z0-9_-] are accepted.  The file is looked up
        via :func:`_find_icon_file` and served directly from disk.
        """
        if not _ICON_NAME_RE.match(icon_name):
            self.send_error(400, "Invalid icon name")
            return

        result = _find_icon_file(icon_name)
        if result is None:
            self.send_error(404, "Icon not found")
            return

        filepath, mime = result
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            logger.debug("Client disconnected while serving icon %s", icon_name)
        except Exception as e:
            logger.exception("Error serving icon %s: %s", icon_name, e)
            self.send_error(500, str(e))

    # ------------------------------------------------------------------
    # WebSocket
    # ------------------------------------------------------------------

    def _handle_websocket(self):
        ws = WebSocketHandler.handshake(self)
        if not ws:
            self.send_error(400, "WebSocket handshake failed")
            return

        if self.dialog:
            self.dialog._register_websocket(ws)

        def on_message(message: str):
            try:
                data = json.loads(message)
                # Always route to the topmost open dialog so that popup
                # dialogs receive events while they are active.
                from .dialogweb import YDialogWeb
                topmost = YDialogWeb.currentDialog(doThrow=False)
                target = topmost if topmost is not None else self.dialog
                if target:
                    target._handle_ws_message(data)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in WebSocket message: %s", message)

        def on_close():
            if self.dialog:
                self.dialog._unregister_websocket(ws)

        ws.on_message = on_message
        ws.on_close = on_close
        ws.run()

        # The WebSocket session is over.  Disable wfile so that
        # handle_one_request()'s cleanup path cannot write to the socket.
        try:
            self.wfile = open(os.devnull, "wb")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # HTTP event fallback
    # ------------------------------------------------------------------

    def _handle_event_post(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            from .dialogweb import YDialogWeb
            topmost = YDialogWeb.currentDialog(doThrow=False)
            target = topmost if topmost is not None else self.dialog
            if target:
                target._handle_ws_message(data)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        except Exception as e:
            logger.exception("Error handling event POST: %s", e)
            self.send_error(500, str(e))

    # ------------------------------------------------------------------
    # SSE fallback
    # ------------------------------------------------------------------

    def _serve_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            while True:
                self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
                threading.Event().wait(30)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Server infrastructure
# ---------------------------------------------------------------------------

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """HTTP server that handles each request in a dedicated thread."""
    allow_reuse_address = True
    daemon_threads = True


class WebServer:
    """
    Main web server for the ManaTools web backend.

    Manages HTTP server lifecycle, WebSocket connections, and serves the
    dialog UI.
    """

    def __init__(
        self,
        dialog: "YDialogWeb",
        host: str = "127.0.0.1",
        port: int = 0,
    ):
        self.dialog = dialog
        self.host = host
        self.port = port
        self._server: Optional[ThreadedHTTPServer] = None
        self._running = False
        self._lock = threading.Lock()

    def start(self):
        """Start the HTTP server (blocking)."""
        with self._lock:
            if self._running:
                return

            handler_class = type(
                "DialogRequestHandler",
                (ManaToolsRequestHandler,),
                {"dialog": self.dialog},
            )
            self._server = ThreadedHTTPServer((self.host, self.port), handler_class)
            self.port = self._server.server_address[1]
            self._running = True

        logger.info("Web server started at %s", self.get_url())
        try:
            self._server.serve_forever()
        except Exception as e:
            logger.exception("Server error: %s", e)
        finally:
            self._running = False

    def stop(self):
        """Stop the HTTP server."""
        with self._lock:
            if self._server and self._running:
                self._server.shutdown()
                self._running = False

    def get_url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    def is_running(self) -> bool:
        return self._running