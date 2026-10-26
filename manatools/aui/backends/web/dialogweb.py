# -*- coding: utf-8 -*-
"""
Web backend dialog implementation.

Author: Matteo Pasotti <xquiet@coriolite.com>

License: LGPLv2+

YDialogWeb is the main container for web-based UI.  Every dialog runs on the
one process-wide HTTP/WebSocket server (see server.get_server()), so the URL
the browser was given stays valid while dialogs come and go; each dialog owns
its event queue and the event loop for user interaction.
"""

import itertools
import math
import queue
import re
import threading
import time
import logging
import json
from typing import Optional, List, TYPE_CHECKING
from importlib.resources import files

from ...yui_common import (
    YSingleChildContainerWidget,
    YDialogType,
    YDialogColorMode,
    YEvent,
    YWidgetEvent,
    YCancelEvent,
    YTimeoutEvent,
    YKeyEvent,
    YMenuEvent,
    YEventReason,
    YUINoDialogException,
    context_menu_items,
    context_menu_item_path,
    has_selectable_item,
)
from .commonweb import escape_html, escape_attr

if TYPE_CHECKING:
    from .server import WebServer

logger = logging.getLogger("manatools.aui.web.YDialogWeb")

# Icon names the /icon/<name> route accepts (same rule as server.py).
_ICON_NAME_RE = re.compile(r'^[a-zA-Z0-9_\-]+$')

_CONTEXT_MENU_SOURCES = ("pointer", "keyboard", "touch")

# ---------------------------------------------------------------------------
# Page builder
# ---------------------------------------------------------------------------

class PageBuilder:
    """
    Builds the full HTML page by loading ``templates/dialog.html`` from the
    package and substituting the three runtime slots:

    * ``{{ id }}``          - dialog id
    * ``{{ title }}``       - dialog title
    * ``{{ classes }}``     - dialog classes
    * ``{{ content }}``     - rendered content

    The template is read from disk exactly once (class-level cache) so
    repeated requests pay no I/O cost.
    """

    _template: Optional[str] = None
    _template_lock = threading.Lock()

    @classmethod
    def _load_template(cls) -> str:
        if cls._template is None:
            with cls._template_lock:
                if cls._template is None:
                    cls._template = (
                        files("manatools.aui.backends.web")
                        .joinpath("templates/dialog.html")
                        .read_text(encoding="utf-8")
                    )
        return cls._template

    @classmethod
    def build(cls, *, _id: str, title: str, classes: str, content: str) -> str:
        """Return the complete HTML dialog as a string."""
        return (
            cls._load_template()
            .replace("{{ id }}", _id)
            .replace("{{ classes }}", classes)
            .replace("{{ title }}", title)
            .replace("{{ content }}", content)
        )


class YDialogWeb(YSingleChildContainerWidget):
    """
    Web-based dialog implementation.

    Manages an HTTP server to serve the dialog as HTML and uses WebSocket
    for real-time event communication with the browser.
    """

    _open_dialogs: List["YDialogWeb"] = []
    _open_dialogs_lock: threading.RLock = threading.RLock()
    # Bumped on every open(); orders main dialogs by when they were opened.
    _open_counter = 0

    # Polling slice used by waitForEvent() so Ctrl-C stays deliverable.
    _WAIT_SLICE = 0.2

    # Context menu ids are unique process-wide, so a pick for a menu of a
    # dialog that has gone can never match a newer one.  next() on a count
    # is atomic, whichever thread or dialog asks.
    _context_menu_ids = itertools.count(1)

    def __init__(self, dialog_type=YDialogType.YMainDialog, color_mode=YDialogColorMode.YDialogNormalColor):
        # Context menu state is touched by server threads (browser messages)
        # and the application thread (openContextMenu), always under the lock.
        self._context_lock = threading.Lock()
        self._context_menu_request = None  # pending ContextMenuActivated request
        self._context_menu_state = None    # menu currently shown in the browser
        super().__init__()
        self._dialog_type = dialog_type
        self._color_mode = color_mode
        self._is_open = False
        self._event_queue: queue.Queue = queue.Queue()
        self._server: Optional["WebServer"] = None  # the shared server, once open
        self._open_seq = 0
        self._default_button = None
        self._widget_registry: dict = {}  # id -> widget mapping
        self._pending_updates: dict = {}  # widget_id -> threading.Timer
        self._pending_lock = threading.Lock()

        with YDialogWeb._open_dialogs_lock:
            YDialogWeb._open_dialogs.append(self)
        logger.debug("YDialogWeb created: %s", self.debugLabel())

    def widgetClass(self):
        return "YDialog"

    @staticmethod
    def currentDialog(doThrow=True) -> Optional["YDialogWeb"]:
        """Return the topmost open dialog, or raise if none."""
        with YDialogWeb._open_dialogs_lock:
            if YDialogWeb._open_dialogs:
                return YDialogWeb._open_dialogs[-1]
        if doThrow:
            raise YUINoDialogException("No dialog is currently open")
        return None

    @staticmethod
    def topmostDialog(doThrow=True) -> Optional["YDialogWeb"]:
        """Same as currentDialog."""
        return YDialogWeb.currentDialog(doThrow=doThrow)

    @staticmethod
    def _root_dialog() -> Optional["YDialogWeb"]:
        """Return the most recently opened main dialog still open, or None.

        It is the dialog the browser page shows; popups sit over it as modal
        overlays.
        """
        with YDialogWeb._open_dialogs_lock:
            mains = [
                d for d in YDialogWeb._open_dialogs
                if d._is_open and d._dialog_type == YDialogType.YMainDialog
            ]
        return max(mains, key=lambda d: d._open_seq) if mains else None

    def isTopmostDialog(self) -> bool:
        """Return whether this dialog is the topmost."""
        with YDialogWeb._open_dialogs_lock:
            return YDialogWeb._open_dialogs[-1] == self if YDialogWeb._open_dialogs else False

    def render_modal_html(self, depth: int = 0) -> str:
        """Render dialog content as a modal overlay fragment (no full page).

        The overlay id is derived from the dialog id so that several popups can
        coexist in the DOM: a file dialog opened from a popup must not evict the
        popup that opened it.  *depth* raises the stacking order so the newest
        overlay sits above the ones already shown.
        """
        content = self.child().render() if self.child() else ""
        overlay_id = escape_attr(self._modal_element_id())
        style = f' style="z-index: {1050 + depth}"' if depth else ""
        hidden = "" if self._visible else " hidden"
        return (
            f'<div id="{overlay_id}" class="mana-popup-overlay"'
            f' data-dialog-id="{escape_attr(self.id())}"{style}{hidden}>'
            f'<div class="mana-popup-container">{content}</div>'
            f'</div>'
        )

    def _modal_element_id(self) -> str:
        """Return the DOM id of this dialog's modal overlay."""
        return f"mana-popup-modal-{self.id()}"

    def _modal_depth(self) -> int:
        """Return how many popups are already open below this one.

        Callers must already hold _open_dialogs_lock.
        """
        return sum(
            1 for d in YDialogWeb._open_dialogs
            if d is not self and d._is_open
            and d._dialog_type != YDialogType.YMainDialog
        )

    def open(self):
        """
        Show the dialog on the process-wide server, starting it if needed.

        A popup is pushed as a modal overlay over whatever the page shows.  A
        main dialog becomes the page itself: connected browsers are told to
        reload.  This is non-blocking - call waitForEvent() to process events.
        """
        if self._is_open:
            return

        self._build_widget_registry()

        from .server import get_server
        server = get_server()
        self._server = server

        with YDialogWeb._open_dialogs_lock:
            YDialogWeb._open_counter += 1
            self._open_seq = YDialogWeb._open_counter
            depth = self._modal_depth()
            self._is_open = True

        if self._dialog_type != YDialogType.YMainDialog:
            self._broadcast({
                "type": "show_modal",
                "dialog_id": self.id(),
                "element_id": self._modal_element_id(),
                "html": self.render_modal_html(depth),
            })
        elif server.has_clients():
            self._broadcast({"type": "reload"})

        server.announce()

    def isOpen(self) -> bool:
        return self._is_open

    def waitForEvent(self, timeout_millisec: int = 0) -> YEvent:
        """
        Block until an event is received from the browser.

        The wait is performed in short slices rather than one blocking get():
        a plain ``queue.get()`` with no timeout parks in ``not_empty.wait()``,
        where Ctrl-C surfaces as a bare KeyboardInterrupt traceback through the
        whole application stack.  Polling lets the interrupt be turned into a
        YCancelEvent, which applications already handle as "close the dialog".

        Args:
            timeout_millisec: Timeout in milliseconds (0 = no timeout)

        Returns:
            YEvent (YWidgetEvent, YCancelEvent, YTimeoutEvent, etc.)
        """
        if not self._is_open:
            self.open()

        deadline = (
            time.monotonic() + timeout_millisec / 1000.0
            if timeout_millisec > 0 else None
        )

        while True:
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return YTimeoutEvent()
                slice_timeout = min(self._WAIT_SLICE, remaining)
            else:
                slice_timeout = self._WAIT_SLICE

            try:
                return self._event_queue.get(timeout=slice_timeout)
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                logger.info("Interrupted while waiting for events, cancelling dialog")
                return YCancelEvent()

    def destroy(self, doThrow=True) -> bool:
        """Close the dialog; the server and the browser connections stay.

        A popup hides its modal overlay.  A main dialog that the page was
        showing makes the browser reload onto what is left, or wait idle for
        the application's next dialog.  Only YUIWeb.shutdown() (or interpreter
        exit) tells the browser the application has gone.
        """
        logger.debug("Destroying dialog: %s", self.debugLabel())

        with self._pending_lock:
            pending = list(self._pending_updates.values())
            self._pending_updates.clear()
        for timer in pending:
            timer.cancel()

        with self._context_lock:
            self._context_menu_request = None
            self._context_menu_state = None

        was_open = self._is_open
        was_root = was_open and YDialogWeb._root_dialog() is self
        self._is_open = False
        with YDialogWeb._open_dialogs_lock:
            if self in YDialogWeb._open_dialogs:
                YDialogWeb._open_dialogs.remove(self)
            popups_left = any(
                d._is_open and d._dialog_type != YDialogType.YMainDialog
                for d in YDialogWeb._open_dialogs
            )

        if not was_open:
            return True

        try:
            if self._dialog_type != YDialogType.YMainDialog:
                self._broadcast({
                    "type": "hide_modal",
                    "dialog_id": self.id(),
                    "element_id": self._modal_element_id(),
                })
            elif was_root:
                if YDialogWeb._root_dialog() is not None or popups_left:
                    # The page re-renders the next root (or an empty shell)
                    # and the ready replay brings the popups back.
                    self._broadcast({"type": "reload"})
                else:
                    self._broadcast({"type": "idle"})
        except Exception:
            logger.debug("destroy: broadcast failed", exc_info=True)

        return True

    @classmethod
    def deleteTopmostDialog(cls, doThrow=True) -> bool:
        """Delete the topmost dialog."""
        with cls._open_dialogs_lock:
            if not cls._open_dialogs:
                return False
            dialog = cls._open_dialogs[-1]
        return dialog.destroy(doThrow)

    @classmethod
    def deleteAllDialogs(cls, doThrow=True) -> bool:
        """Delete all open dialogs."""
        ok = True
        while True:
            with cls._open_dialogs_lock:
                if not cls._open_dialogs:
                    break
                dialog = cls._open_dialogs[-1]
            try:
                dialog.destroy(doThrow)
            except Exception:
                ok = False
                with cls._open_dialogs_lock:
                    try:
                        cls._open_dialogs.remove(dialog)
                    except ValueError:
                        break
        return ok

    def setDefaultButton(self, button) -> bool:
        """Set the default button for this dialog."""
        if button is None:
            self._default_button = None
            return True

        try:
            if button.widgetClass() != "YPushButton":
                logger.error("Default button must be a YPushButton")
                return False
        except Exception:
            return False

        self._default_button = button
        return True

    def _post_event(self, event: YEvent):
        """Post an event to the dialog's event queue."""
        self._event_queue.put(event)

    def _broadcast(self, message: dict):
        """Broadcast a message to every browser connected to the server."""
        from .server import current_server
        server = current_server()
        if server is not None:
            server.broadcast(message)

    def _handle_ws_message(self, data: dict):
        """Handle a message received via WebSocket."""
        if not isinstance(data, dict):
            logger.warning("Ignoring non-object WebSocket message")
            return
        msg_type = data.get("type", "")

        if msg_type == "event":
            self._handle_widget_event(data)
        elif msg_type == "table_checkbox":
            self._handle_table_checkbox(data)
        elif msg_type == "link_activated":
            self._handle_link_activation(data)
        elif msg_type == "ready":
            self._handle_browser_ready()
        elif msg_type == "close":
            self._post_event(YCancelEvent())
        elif msg_type == "key":
            self._handle_key_event(data)
        elif msg_type == "context_menu":
            self._handle_context_menu_result(data)
        else:
            logger.warning("Unknown WebSocket message type: %s", msg_type)

    def _handle_widget_event(self, data: dict):
        """Handle a widget event from the browser."""
        widget_id = data.get("widget_id", "")
        reason_str = data.get("reason", "Activated")
        event_data = data.get("data", {})
        if not isinstance(event_data, dict):
            event_data = {}

        widget = self._lookup_widget(widget_id)
        if not widget:
            logger.warning("Widget not found: %s", widget_id)
            return

        reason_map = {
            "Activated":            YEventReason.Activated,
            "ValueChanged":         YEventReason.ValueChanged,
            "SelectionChanged":     YEventReason.SelectionChanged,
            "ContextMenuActivated": YEventReason.ContextMenuActivated,
        }
        reason = reason_map.get(reason_str, YEventReason.Activated)

        # A context request carries a row reference, not a selection: it must
        # not reach the generic value/selection handling below.
        if reason == YEventReason.ContextMenuActivated:
            self._handle_context_menu_request(widget, event_data)
            return

        if "value" in event_data:
            if hasattr(widget, "setValue"):
                widget.setValue(event_data["value"])
            elif hasattr(widget, "_value"):
                widget._value = event_data["value"]

        if "checked" in event_data:
            # YCheckBoxFrame has no setChecked(): setValue() is its boolean setter.
            if hasattr(widget, "setChecked"):
                widget.setChecked(event_data["checked"])
            elif hasattr(widget, "setValue"):
                widget.setValue(bool(event_data["checked"]))

        # Tree item selection ? uses a stable item id instead of a
        # flat index because tree items are nested.
        if "itemId" in event_data:
            if hasattr(widget, '_handle_item_click'):
                widget._handle_item_click(event_data["itemId"])
 
        # (existing selectedIndex / selectedValue block follows unchanged)
        if "selectedIndex" in event_data or "selectedValue" in event_data:
            if hasattr(widget, "_handle_selection_change"):
                # Prefer value-based lookup: avoids off-by-one caused by a
                # non-selectable label <option> at index 0 in the rendered HTML.
                selected_value = event_data.get("selectedValue")
                selected_index = event_data.get("selectedIndex", 0)
                widget._handle_selection_change(selected_index, selected_value)

        # Menu bar activations carry a menuItem label in event_data.
        # Route these as YMenuEvent so dnfdragora's menu handler fires
        # correctly instead of falling through to the generic widget path.
        if event_data.get("menuItem") is not None and hasattr(widget, 'widgetClass') and widget.widgetClass() == 'YMenuBar':
            menu_label = event_data["menuItem"]
            item_id = event_data.get("itemId")
            matched_item = None
            if hasattr(widget, '_menus'):
                def _find_by_id(items, target_id):
                    for m in items:
                        if hasattr(m, '_children'):
                            for child in m._children:
                                if id(child) == target_id:
                                    return child
                                result = _find_by_id([child], target_id)
                                if result:
                                    return result
                    return None

                def _find_by_label(items, label):
                    from .commonweb import strip_shortcut
                    for m in items:
                        if hasattr(m, '_children'):
                            for child in m._children:
                                if not getattr(child, 'isSeparator', lambda: False)() and strip_shortcut(child.label()) == label:
                                    return child
                                result = _find_by_label([child], label)
                                if result:
                                    return result
                    return None

                if item_id is not None:
                    try:
                        matched_item = _find_by_id(widget._menus, int(item_id))
                    except (ValueError, TypeError):
                        pass
                if matched_item is None:
                    matched_item = _find_by_label(widget._menus, menu_label)
            event = YMenuEvent(item=matched_item, id=menu_label)
        else:
            event = YWidgetEvent(widget, reason)
        self._post_event(event)

    # ------------------------------------------------------------------
    # Context menus
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_int(value, low, high):
        """Return value as an int clamped to [low, high], or None if it is not a number."""
        if isinstance(value, bool):
            return None
        if isinstance(value, str):
            try:
                value = float(value.strip())
            except ValueError:
                return None
        if not isinstance(value, (int, float)):
            return None
        if isinstance(value, float):
            if not math.isfinite(value):
                return None
            value = int(round(value))
        return max(low, min(high, value))

    def _handle_context_menu_request(self, widget, event_data: dict):
        """Turn a browser right-click (or Menu key) on widget into ContextMenuActivated.

        Mirrors the Qt/curses backends: an unselected row becomes the only
        selected row first, so the handler can rely on selectedItem(); inside a
        selection it is kept.  The request is remembered until openContextMenu().
        """
        if not widget.notifyContextMenu():
            logger.debug("context menu request ignored: notify off for %s", widget.debugLabel())
            return
        if not widget.isEnabled():
            return

        ref = None
        item_id = event_data.get("itemId")
        if isinstance(item_id, str) and 0 < len(item_id) <= 256:
            ref = item_id
        elif "rowIndex" in event_data:
            row = event_data.get("rowIndex")
            if not isinstance(row, bool) and isinstance(row, (int, float)):
                ref = self._coerce_int(row, -1, 2 ** 31)
        if ref is not None and hasattr(widget, "_context_menu_select"):
            try:
                widget._context_menu_select(ref)
            except Exception:
                logger.exception("context menu selection failed for %s", widget.debugLabel())

        source = event_data.get("source")
        request = {
            "widget": widget,
            "x": self._coerce_int(event_data.get("clientX"), 0, 1000000) or 0,
            "y": self._coerce_int(event_data.get("clientY"), 0, 1000000) or 0,
            "source": source if source in _CONTEXT_MENU_SOURCES else "pointer",
            "seq": self._coerce_int(event_data.get("seq"), 0, 2 ** 53 - 1) or 0,
        }
        with self._context_lock:
            self._context_menu_request = request
        self._post_event(YWidgetEvent(widget, YEventReason.ContextMenuActivated))

    @staticmethod
    def _context_menu_icon_url(icon_name) -> str:
        """Return the /icon/ URL for a bare XDG icon name, or ''."""
        if not icon_name or not isinstance(icon_name, str):
            return ""
        name = icon_name.rsplit(".", 1)[0] if "." in icon_name else icon_name
        return f"/icon/{name}" if _ICON_NAME_RE.match(name) else ""

    @classmethod
    def _serialize_context_menu(cls, items, id_map, pickable, reachable=True) -> list:
        """Snapshot the visible items as JSON-ready dicts.

        Fills id_map (id -> YMenuItem) and pickable (ids of the enabled leaves
        reachable through enabled submenus).  Labels are sent raw (mnemonic
        included): the browser builds the menu with textContent, so nothing
        here is ever interpreted as HTML.
        """
        result = []
        for item in items:
            if not item.visible():
                continue
            item_id = len(id_map) + 1
            id_map[item_id] = item
            separator = bool(item.isSeparator())
            submenu = bool(item.isMenu()) and not separator
            if separator:
                enabled = False
            elif submenu:
                enabled = bool(item.enabled()) and has_selectable_item(item._children)
            else:
                enabled = bool(item.enabled())
                if enabled and reachable:
                    pickable.add(item_id)
            children = (cls._serialize_context_menu(item._children, id_map, pickable, reachable and enabled)
                        if submenu else [])
            result.append({
                "id": item_id,
                "label": str(item.label() or ""),
                "icon": "" if separator else cls._context_menu_icon_url(item.iconName()),
                "enabled": enabled,
                "separator": separator,
                "submenu": submenu,
                "items": children,
            })
        return result

    def _open_context_menu(self, items) -> bool:
        """Show a context menu in the browser for the pending request (non-blocking).

        The menu is a snapshot of the current item state, so the app may change
        shared YMenuItem objects freely between openings.  Opening a menu while
        another is shown replaces it without a cancel event.
        """
        top_items = context_menu_items(items)
        with self._context_lock:
            request = self._context_menu_request
            if request is None or not has_selectable_item(top_items):
                return False
            self._context_menu_request = None
            id_map = {}
            pickable = set()
            payload_items = self._serialize_context_menu(top_items, id_map, pickable)
            menu_id = next(YDialogWeb._context_menu_ids)
            self._context_menu_state = {
                "menu_id": menu_id,
                "items": id_map,
                "pickable": pickable,
                "top_items": top_items,
                "widget": request["widget"],
            }
        self._broadcast({
            "type": "show_context_menu",
            "menu_id": menu_id,
            "dialog_id": self.id(),
            "seq": request["seq"],
            "x": request["x"],
            "y": request["y"],
            "source": request["source"],
            "items": payload_items,
        })
        return True

    def _handle_context_menu_result(self, data: dict):
        """Handle the browser's answer to show_context_menu: a pick or a dismissal."""
        menu_id = self._coerce_int(data.get("menu_id"), 0, 2 ** 53 - 1)
        cancelled = data.get("cancelled") is True
        item_id = None if cancelled else self._coerce_int(data.get("item_id"), 0, 2 ** 31)
        with self._context_lock:
            state = self._context_menu_state
            if state is None or menu_id is None or state["menu_id"] != menu_id:
                logger.debug("context_menu: stale or unknown menu id %r", data.get("menu_id"))
                return
            item = None
            if not cancelled:
                item = state["items"].get(item_id) if item_id in state["pickable"] else None
                if item is None or not item.enabled():
                    logger.debug("context_menu: invalid item %r", data.get("item_id"))
                    return
            self._context_menu_state = None
        source = state["widget"]
        if cancelled:
            self._post_event(YWidgetEvent(source, YEventReason.ContextMenuCancelled))
        else:
            self._post_event(YMenuEvent(item=item, id=context_menu_item_path(item, state["top_items"]),
                                        widget=source))

    def _cancel_context_menu(self):
        """Drop the open menu, if any, posting ContextMenuCancelled for it."""
        with self._context_lock:
            state = self._context_menu_state
            self._context_menu_state = None
            self._context_menu_request = None
        if state is not None:
            self._post_event(YWidgetEvent(state["widget"], YEventReason.ContextMenuCancelled))

    def _handle_key_event(self, data: dict):
        """Handle a keyboard event from the browser."""
        key = data.get("key", "")
        widget_id = data.get("widget_id", "")

        widget = self._lookup_widget(widget_id)
        event = YKeyEvent(key, widget)
        self._post_event(event)

    def _handle_table_checkbox(self, data: dict):
        """Handle a checkbox-cell toggle inside a YTable.

        Mirrors Qt setData(CheckStateRole): routes to the widget's
        _handle_checkbox_change so it can update the cell model and fire events.
        """
        widget_id = data.get("widget_id", "")
        widget = self._lookup_widget(widget_id)
        if widget is None:
            logger.warning("table_checkbox: widget not found: %s", widget_id)
            return
        if hasattr(widget, '_handle_checkbox_change'):
            widget._handle_checkbox_change(
                int(data.get("row", 0)),
                int(data.get("col", 0)),
                bool(data.get("checked", False)),
            )

    def _handle_link_activation(self, data: dict):
        """Handle a link click inside a YRichText widget.

        Mirrors Qt/GTK behaviour: prevent navigation, store the URL in the
        widget, and post a YMenuEvent if the widget has notify() enabled.
        """
        widget_id = data.get("widget_id", "")
        url = data.get("url", "")
        widget = self._lookup_widget(widget_id)
        if widget is None:
            logger.warning("link_activated: widget not found: %s", widget_id)
            return
        if hasattr(widget, '_last_url'):
            widget._last_url = url
        if hasattr(widget, 'notify') and widget.notify():
            self._post_event(YMenuEvent(item=None, id=url))

    def _handle_browser_ready(self):
        """Bring a freshly connected browser up to date.

        A popup opened before any browser was connected broadcasts its
        ``show_modal`` message to nobody: the application then blocks in
        waitForEvent() on a dialog the user cannot see or dismiss.  Replaying
        the open popups here makes the modal appear as soon as the page
        connects, whatever the order was on the Python side.

        Whichever dialog receives ``ready`` (the topmost), the deferred table
        rows belong to the root dialog: that is what the page rendered.

        A context menu shown before is not replayed: it counts as dismissed.
        """
        with YDialogWeb._open_dialogs_lock:
            dialogs = list(YDialogWeb._open_dialogs)
        for dlg in dialogs:
            dlg._cancel_context_menu()
        self._replay_open_modals()
        root = YDialogWeb._root_dialog()
        if root is not None:
            root._push_deferred_tables()
        elif not any(d._is_open for d in list(YDialogWeb._open_dialogs)):
            self._broadcast({"type": "idle"})

    def _replay_open_modals(self):
        """Re-send ``show_modal`` for every open popup dialog.

        Sent in stack order, so a browser that connects (or reconnects) while
        several popups are open rebuilds the whole stack, not just its top.
        """
        with YDialogWeb._open_dialogs_lock:
            popups = [
                d for d in YDialogWeb._open_dialogs
                if d._is_open and d._dialog_type != YDialogType.YMainDialog
            ]

        for depth, popup in enumerate(popups):
            try:
                self._broadcast({
                    "type": "show_modal",
                    "dialog_id": popup.id(),
                    "element_id": popup._modal_element_id(),
                    "html": popup.render_modal_html(depth),
                })
            except Exception:
                logger.exception("Failed to replay modal for %s", popup.debugLabel())

    def _push_deferred_tables(self):
        """Push table row content to all connected clients.

        Called when the browser sends a ``ready`` message (WS open).  Only
        tables that actually rendered a loading skeleton (``_deferred_pending``
        is True) are included so we never blindly overwrite a table that was
        already fully rendered.  Each widget is rendered inside a try/except so
        one broken widget cannot prevent the others from loading.
        """
        updates = []
        for widget_id, widget in self._widget_registry.items():
            if not getattr(widget, '_deferred_pending', False):
                continue
            try:
                html = widget._render_rows_html()
                widget._deferred_pending = False
                updates.append({
                    "action": "rows",
                    "target": f"#{widget_id}",
                    "html": html,
                })
            except Exception:
                logger.exception("_push_deferred_tables: failed to render rows for %s", widget_id)
        if updates:
            self._broadcast({"type": "update", "updates": updates})

    def _build_widget_registry(self):
        """Build a mapping of widget IDs to widget objects."""
        self._widget_registry.clear()
        self._register_widget_tree(self)

    def _lookup_widget(self, widget_id):
        """Return the widget with *widget_id*, or None.

        The registry is built at open(); widgets created afterwards (e.g. new
        children of a YReplacePoint) are picked up by rebuilding it on a miss.
        """
        widget = self._widget_registry.get(widget_id)
        if widget is None and widget_id:
            self._build_widget_registry()
            widget = self._widget_registry.get(widget_id)
        return widget

    def _register_widget_tree(self, widget):
        """Recursively register all widgets in the tree."""
        self._widget_registry[widget.id()] = widget

        if hasattr(widget, '_children'):
            for child in widget._children:
                self._register_widget_tree(child)

    def _schedule_update(self, widget):
        """Schedule a UI update for a widget.

        Rapid successive calls for the same widget within a short window are
        coalesced: only the last state is broadcast.  This prevents multiple
        stale intermediate renders arriving at the browser out of order when
        application code mutates a widget in several steps (e.g. deleteAllItems
        -> setLabel -> addItems).
        """
        widget_id = widget.id()
        with self._pending_lock:
            existing = self._pending_updates.get(widget_id)
            if existing is not None:
                existing.cancel()
            timer = threading.Timer(
                0.05,  # 50 ms coalesce window
                self._flush_update,
                args=(widget,),
            )
            self._pending_updates[widget_id] = timer
            timer.start()

    def _flush_all_pending_updates(self):
        """Cancel all coalesce timers and broadcast every queued widget update immediately.

        Called by normalCursor() so that the busy overlay is only hidden after
        all pending DOM updates have already been sent to the browser.
        """
        with self._pending_lock:
            pending = list(self._pending_updates.items())
            self._pending_updates.clear()

        for _widget_id, timer in pending:
            timer.cancel()
            if timer.args:
                self._flush_update(timer.args[0])

    def _flush_update(self, widget):
        """Actually broadcast the update for a widget (called by the timer).
 
        If the widget exposes a ``render_update()`` method it is called instead
        of ``render()`` so that widgets with static parts (e.g. a label that
        must not be duplicated on every value change, like YProgressBar) can
        return a precise (selector, html) pair targeting only their dynamic
        inner element.

        ``render_update()`` may return either a 2-tuple ``(target, html)``
        (action defaults to ``"replace"``) or a 3-tuple
        ``(target, html, action)`` where *action* may be ``"replace"`` or
        ``"html"``.  The ``"html"`` action sets ``innerHTML`` on the target
        element without removing and re-inserting it, keeping its DOM position
        stable.

        Falls back to the original behaviour for all other widgets:
        targets ``[data-container-for="<id>"]`` first so that widgets that
        wrap themselves in a container div (e.g. ComboBox with a label) are
        replaced atomically, then falls back to ``#<id>`` for simple widgets.
        """
        with self._pending_lock:
            self._pending_updates.pop(widget.id(), None)
        try:
            if hasattr(widget, 'render_update'):
                result = widget.render_update()
                if len(result) == 3:
                    target, html, action = result
                else:
                    target, html = result
                    action = "replace"
            else:
                html = widget.render()
                target = f'[data-container-for="{widget.id()}"], #{widget.id()}'
                action = "replace"

            self._broadcast({
                "type": "update",
                "updates": [{
                    "action": action,
                    "target": target,
                    "html": html,
                }]
            })
        except Exception as e:
            logger.exception("Failed to flush update: %s", e)

    def render(self) -> str:
        """Render the dialog to HTML."""
        title = "ManaTools"
        try:
            from ...yui import YUI
            app = YUI.application()
            if app:
                title = app.applicationTitle() or title
        except Exception:
            pass

        type_class = {
            YDialogType.YMainDialog:   "main",
            YDialogType.YPopupDialog:  "popup",
            YDialogType.YWizardDialog: "wizard",
        }.get(self._dialog_type, "main")

        color_class = {
            YDialogColorMode.YDialogNormalColor: "",
            YDialogColorMode.YDialogInfoColor:   "info",
            YDialogColorMode.YDialogWarnColor:   "warn",
        }.get(self._color_mode, "")

        classes = f"mana-dialog mana-dialog-{type_class}"
        if color_class:
            classes += f" mana-dialog-{color_class}"

        content = self.child().render() if self.child() else ""
        html = PageBuilder.build(
            _id=self.id(),
            title=escape_html(title),
            classes=classes,
            content=content,
        )
        if not self._visible:
            html = html.replace(f'<div id="{self.id()}"', f'<div hidden id="{self.id()}"', 1)
        return html

    def setVisible(self, visible: bool = True):
        """Show or hide the dialog (main page content, or a popup overlay)."""
        self._visible = bool(visible)
        if not self._is_open:
            return
        target = (f"#{self.id()}" if self._dialog_type == YDialogType.YMainDialog
                  else f"#{self._modal_element_id()}")
        self._broadcast({
            "type": "update",
            "updates": [{"action": "attr", "target": target,
                         "attr": "hidden", "value": None if self._visible else True}],
        })