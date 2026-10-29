# -*- coding: utf-8 -*-
"""
HTTP and WebSocket server for the web backend.

License: LGPLv2+

Author:  Matteo Pasotti <xquiet@coriolite.com>

This module provides a simple HTTP server that serves the dialog HTML
and handles WebSocket connections for real-time event communication.
"""

import atexit
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

    # Maximum accepted incoming frame payload (16 MB).  Frames larger than
    # this are rejected immediately so a rogue client cannot exhaust memory.
    MAX_FRAME_SIZE = 16 * 1024 * 1024

    # Hostnames / addresses considered local.  Only WebSocket upgrades and
    # /event POST requests whose Origin matches one of these are accepted.
    _LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

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

    # ------------------------------------------------------------------
    # Origin validation (shared by WS handshake and /event POST)
    # ------------------------------------------------------------------

    @classmethod
    def _is_local_origin(cls, origin: Optional[str]) -> bool:
        """Return True if *origin* is absent or points to localhost.

        An absent Origin header is allowed so that curl / direct browser
        address-bar requests work.  A ``null`` origin (file://) is also
        accepted.  Any other origin whose host is not in _LOCAL_HOSTS is
        rejected to prevent DNS-rebinding and CSRF attacks.
        """
        if origin is None or origin == "null":
            return True
        try:
            parsed = urlparse(origin)
            # urlparse stores host without port in .hostname
            return parsed.hostname in cls._LOCAL_HOSTS
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Handshake
    # ------------------------------------------------------------------

    @classmethod
    def handshake(cls, request_handler) -> Optional["WebSocketHandler"]:
        """Perform WebSocket handshake. Returns WebSocketHandler on success."""
        try:
            origin = request_handler.headers.get("Origin")
            if not cls._is_local_origin(origin):
                request_handler.send_error(403, "Forbidden: non-local origin")
                logger.warning("WebSocket upgrade rejected for origin: %s", origin)
                return None

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

    # ------------------------------------------------------------------
    # Frame I/O
    # ------------------------------------------------------------------

    def _recv_exact(self, n: int) -> bytes:
        """Read exactly *n* bytes from the socket.

        Unlike a bare ``recv(n)`` call, this loops until all bytes arrive or
        the connection is closed, preventing silent truncation on slow or
        fragmented TCP streams.

        Raises ``ConnectionError`` if the peer closes the connection before
        *n* bytes are delivered.
        """
        buf = bytearray()
        while len(buf) < n:
            chunk = self.request.recv(n - len(buf))
            if not chunk:
                raise ConnectionError(
                    f"Connection closed after {len(buf)} of {n} bytes"
                )
            buf.extend(chunk)
        return bytes(buf)

    def receive_frame(self) -> Optional[str]:
        """Receive a WebSocket frame and return the text payload."""
        try:
            header = self._recv_exact(2)

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
                payload_len = struct.unpack(">H", self._recv_exact(2))[0]
            elif payload_len == 127:
                payload_len = struct.unpack(">Q", self._recv_exact(8))[0]

            if payload_len > self.MAX_FRAME_SIZE:
                self._closed = True
                logger.warning(
                    "WebSocket frame too large (%d bytes); closing connection",
                    payload_len,
                )
                return None

            mask_key = self._recv_exact(4) if masked else b""
            payload = self._recv_exact(payload_len)

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

    # Injected by WebServer via a per-server subclass
    web_server: Optional["WebServer"] = None

    def log_message(self, format, *args):
        logger.debug(format, *args)

    _DEFAULT_CSP = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none';"
    )

    def _send_security_headers(self, csp: Optional[str] = None,
                               frame_options: str = "DENY",
                               referrer: str = "same-origin"):
        """Emit HTTP security headers on every successful response.

        * CSP: restricts scripts/fonts/images to same origin; allows inline
          styles because Bootstrap JS sets ``style=""`` attributes at runtime.
          WebSocket connections back to the same host are explicitly permitted.
        * X-Content-Type-Options: prevents MIME-type sniffing.
        * X-Frame-Options: prevents the page being embedded in an iframe.
        * Referrer-Policy: prevents leaking the URL to third-party requests.

        The only caller overriding the defaults is the YHtmlView document
        route, whose response must be frameable by our own page and carries a
        far stricter CSP of its own.
        """
        self.send_header("Content-Security-Policy", csp or self._DEFAULT_CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", frame_options)
        self.send_header("Referrer-Policy", referrer)

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
        elif path.startswith("/htmlview/"):
            self._serve_htmlview(path[len("/htmlview/"):])
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

    @staticmethod
    def _topmost_dialog() -> Optional["YDialogWeb"]:
        """Return the dialog that receives browser events (the topmost one)."""
        from .dialogweb import YDialogWeb
        return YDialogWeb.currentDialog(doThrow=False)

    def _serve_main_page(self):
        """Render the root (main) dialog, or an empty shell when none is open.

        Popups are not part of the page: the ``ready`` replay pushes them as
        modal overlays, so a popup opened before any main dialog looks the
        same as one opened over it.
        """
        try:
            from .commonweb import set_initial_render
            from .dialogweb import YDialogWeb
            title = self._resolve_title()
            root = YDialogWeb._root_dialog()
            dialog_html = ""
            if root is not None:
                set_initial_render(True)
                try:
                    dialog_html = root.render()
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
            self._send_security_headers()
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

        server = self.web_server
        if server:
            server._register_websocket(ws)

        def on_message(message: str):
            try:
                data = json.loads(message)
                # Always route to the topmost open dialog so that popup
                # dialogs receive events while they are active.
                target = self._topmost_dialog()
                if target:
                    target._handle_ws_message(data)
                elif data.get("type") == "ready":
                    # No dialog at all: the application is between dialogs.
                    ws.send(json.dumps({"type": "idle"}))
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in WebSocket message: %s", message)

        def on_close():
            if server:
                server._unregister_websocket(ws)

        ws.on_message = on_message
        ws.on_close = on_close
        ws.run()

        # The WebSocket session is over.  Disable wfile so that
        # handle_one_request()'s cleanup path cannot write to the socket.
        try:
            devnull = open(os.devnull, "wb")
            old_wfile = self.wfile
            self.wfile = devnull
            try:
                old_wfile.close()
            except Exception:
                pass
        except Exception:
            pass

    # ------------------------------------------------------------------
    # YHtmlView documents
    # ------------------------------------------------------------------

    # <token> for the document, <token>/link/<n> for a link activation.
    _HTMLVIEW_PATH_RE = re.compile(r"^([A-Za-z0-9_-]{16,64})(?:/link/(\d{1,6}))?$")

    @staticmethod
    def _htmlview_csp(allow_remote: bool) -> str:
        """CSP of a YHtmlView document: no script at all, sandboxed, images
        only inline unless the application allowed remote content."""
        img_src = "data: http: https:" if allow_remote else "data:"
        return (
            "default-src 'none'; "
            f"img-src {img_src}; "
            "style-src 'unsafe-inline'; "
            "font-src data:; "
            "base-uri 'none'; "
            "form-action 'none'; "
            "frame-ancestors 'self'; "
            "sandbox"
        )

    def _is_local_host(self) -> bool:
        """True if the Host header names this machine (DNS-rebinding guard)."""
        try:
            hostname = urlparse("//" + self.headers.get("Host", "")).hostname
        except Exception:
            return False
        return hostname in WebSocketHandler._LOCAL_HOSTS

    def _serve_htmlview(self, rest: str):
        """Serve a YHtmlView document, or report one of its links.

        Both are plain GETs issued by a sandboxed frame (opaque origin, no
        script), so the usual Origin check cannot be the only guard: the URL
        carries the widget's unguessable per-content token, the Host must be
        local, and the request must be a frame load.  A link request posts
        the activation and answers 204, which leaves the frame where it is.
        """
        match = self._HTMLVIEW_PATH_RE.match(rest)
        if not match:
            self.send_error(404, "Not Found")
            return
        if (not self._is_local_host()
                or not WebSocketHandler._is_local_origin(self.headers.get("Origin"))):
            self.send_error(403, "Forbidden")
            logger.warning("/htmlview rejected: Host=%s Origin=%s",
                           self.headers.get("Host"), self.headers.get("Origin"))
            return
        fetch_dest = self.headers.get("Sec-Fetch-Dest")
        if fetch_dest is not None and fetch_dest != "iframe":
            self.send_error(403, "Forbidden")
            return

        from .htmlviewweb import YHtmlViewWeb
        token, link = match.group(1), match.group(2)
        widget = YHtmlViewWeb._lookup(token)
        if widget is None:
            self.send_error(404, "Not Found")
            return

        if link is not None:
            widget._serve_link(token, int(link))
            self.send_response(204)
            self._send_security_headers(csp=self._htmlview_csp(False),
                                        frame_options="SAMEORIGIN",
                                        referrer="no-referrer")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return

        served = widget._serve_document(token)
        if served is None:
            self.send_error(404, "Not Found")
            return
        document, allow_remote = served
        encoded = document.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self._send_security_headers(csp=self._htmlview_csp(allow_remote),
                                    frame_options="SAMEORIGIN",
                                    referrer="no-referrer")
        self.end_headers()
        self.wfile.write(encoded)

    # ------------------------------------------------------------------
    # HTTP event fallback
    # ------------------------------------------------------------------

    # Maximum body size accepted from the /event POST fallback endpoint.
    # UI events are tiny JSON objects; anything larger is rejected immediately.
    MAX_POST_BODY = 64 * 1024  # 64 KB

    def _handle_event_post(self):
        origin = self.headers.get("Origin")
        if not WebSocketHandler._is_local_origin(origin):
            self.send_error(403, "Forbidden: non-local origin")
            logger.warning("/event POST rejected for origin: %s", origin)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > self.MAX_POST_BODY:
                self.send_error(413, "Payload Too Large")
                logger.warning("/event POST body too large: %d bytes", length)
                return
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            target = self._topmost_dialog()
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


def _env_port() -> int:
    """Return the port requested via ``MUI_WEB_PORT`` (0 = any free port)."""
    value = os.environ.get("MUI_WEB_PORT", "").strip()
    if not value:
        return 0
    try:
        port = int(value)
        if 0 <= port <= 65535:
            return port
    except ValueError:
        pass
    logger.warning("Ignoring invalid MUI_WEB_PORT=%r", value)
    return 0


class WebServer:
    """
    Main web server for the ManaTools web backend.

    One instance serves the whole process (see :func:`get_server`): dialogs
    come and go on it, so the URL given to the browser stays valid for the
    life of the application.  The handler resolves the dialog to render or
    to route events to on every request.

    The browser WebSocket connections belong to the server as well, and
    :meth:`broadcast` sends to all of them.
    """

    def __init__(self, host: str = "127.0.0.1", port: Optional[int] = None):
        self.host = host
        self.port = _env_port() if port is None else port
        self._server: Optional[ThreadedHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._websockets: list = []
        self._websocket_lock = threading.Lock()
        self._announced = False

    def start(self):
        """Bind the listening socket and serve it from a daemon thread.

        A fixed port that is already taken falls back to a free one, so a
        second instance of an application still comes up.
        """
        with self._lock:
            if self._running:
                return

            handler_class = type(
                "WebServerRequestHandler",
                (ManaToolsRequestHandler,),
                {"web_server": self},
            )
            try:
                self._server = ThreadedHTTPServer((self.host, self.port), handler_class)
            except OSError as e:
                if not self.port:
                    raise
                logger.warning("Port %d unavailable (%s); using a free port", self.port, e)
                self._server = ThreadedHTTPServer((self.host, 0), handler_class)
            self.port = self._server.server_address[1]
            self._running = True
            self._thread = threading.Thread(target=self._serve, daemon=True)
            self._thread.start()

        logger.info("Web server started at %s", self.get_url())

    def _serve(self):
        try:
            self._server.serve_forever()
        except Exception as e:
            logger.exception("Server error: %s", e)
        finally:
            self._running = False

    def stop(self):
        """Close every WebSocket, stop serving and release the port."""
        with self._websocket_lock:
            sockets = list(self._websockets)
            self._websockets.clear()
        for ws in sockets:
            try:
                ws.close()
            except Exception:
                pass

        with self._lock:
            server, self._server = self._server, None
            thread, self._thread = self._thread, None
            self._running = False
        if server:
            # shutdown() waits for serve_forever(), which only a live
            # thread can end.
            if thread is not None and thread.is_alive():
                server.shutdown()
            server.server_close()

    def get_url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    def is_running(self) -> bool:
        return self._running

    def announce(self):
        """Print the URL on the terminal, once per server."""
        if self._announced:
            return
        self._announced = True
        print(f"\n{'='*50}")
        print(f"  Dialog available at: {self.get_url()}")
        print(f"  Open this URL in your web browser")
        print(f"{'='*50}\n")

    # ------------------------------------------------------------------
    # Browser connections
    # ------------------------------------------------------------------

    def _register_websocket(self, ws: WebSocketHandler):
        """Register a new WebSocket connection."""
        with self._websocket_lock:
            self._websockets.append(ws)
            count = len(self._websockets)
        logger.debug("WebSocket connected, total: %d", count)

    def _unregister_websocket(self, ws: WebSocketHandler):
        """Unregister a WebSocket connection."""
        with self._websocket_lock:
            if ws in self._websockets:
                self._websockets.remove(ws)
            count = len(self._websockets)
        logger.debug("WebSocket disconnected, remaining: %d", count)

    def has_clients(self) -> bool:
        """Return whether a browser is connected."""
        with self._websocket_lock:
            return bool(self._websockets)

    def broadcast(self, message: dict):
        """Send *message* to every connected browser."""
        data = json.dumps(message)
        with self._websocket_lock:
            sockets = list(self._websockets)
        for ws in sockets:
            try:
                ws.send(data)
            except Exception as e:
                logger.debug("Failed to send to WebSocket: %s", e)


# ---------------------------------------------------------------------------
# Process-wide server
# ---------------------------------------------------------------------------

_instance: Optional[WebServer] = None
_instance_lock = threading.Lock()


def get_server() -> WebServer:
    """Return the process-wide server, creating and starting it on first use."""
    global _instance
    with _instance_lock:
        if _instance is None:
            server = WebServer()
            server.start()
            _instance = server
            atexit.register(shutdown_server)
        return _instance


def current_server() -> Optional[WebServer]:
    """Return the running server, or None; never starts one."""
    return _instance


def shutdown_server(reason: str = "The application has closed."):
    """Tell the browsers the process is exiting, then stop the server.

    Called by ``YUIWeb.shutdown()`` and at interpreter exit; later calls do
    nothing, so ``shutdown`` is sent once.
    """
    global _instance
    with _instance_lock:
        server, _instance = _instance, None
    if server is None:
        return
    server.broadcast({"type": "shutdown", "reason": reason})
    server.stop()
