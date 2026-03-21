#!/usr/bin/env python3
"""Interactive test for YLogView: HEAD/TAIL focus and normal/reverse display order.

Usage::

    python test_logview.py [backend]      # backend: qt | gtk | ncurses

Scenarios
---------
The internal ``_lines`` buffer is **always** in chronological order
(oldest at index 0, newest at index -1).  The *reverse* flag only
changes how those lines are *rendered*; *focus* controls the scroll
anchor.

The test opens **four** simultaneous log views arranged in two columns:

    Left column  (HEAD focus)   |   Right column (TAIL focus)
    ----------------------------+----------------------------------
    HEAD / normal               |   TAIL / normal
    HEAD / reverse              |   TAIL / reverse

Expected behaviour per case
~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **HEAD / normal** — display order: oldest-at-top, newest-at-bottom.
   Viewport is anchored at the TOP (oldest line).  New lines appear at
   the bottom and the viewport does **not** move automatically.

2. **HEAD / reverse** — display order: newest-at-top, oldest-at-bottom.
   Viewport is anchored at the TOP (newest line).  Because new lines
   are rendered at the top and the viewport stays at row 0, the newest
   line is always visible without any explicit scrolling.

3. **TAIL / normal** — display order: oldest-at-top, newest-at-bottom.
   Viewport auto-scrolls to the BOTTOM on every append so the newest
   line is always visible.

4. **TAIL / reverse** — display order: newest-at-top, oldest-at-bottom.
   Viewport auto-scrolls to the BOTTOM on every append.  In reverse
   order bottom = oldest line.  This is the geometrical **opposite of
   case 1** (case 1: viewport at top = oldest; case 4: viewport at
   bottom = oldest with newest at top).

Buttons
~~~~~~~
* **Append 10 lines (all)** — appends a numbered batch to all four views.
* **Clear (all)** — clears all views and resets the counter.
* **Toggle focus (right col)** — calls ``setFocus()`` to flip TAIL ↔ HEAD
  on the two right-column views at runtime.
* **Toggle reverse (right col)** — calls ``setReverse()`` to flip
  the display order on the right-column views at runtime.  The internal
  buffer is unchanged; only the rendering direction flips.
* **Close**

Ring-buffer: ``storedLines=60`` — once exceeded the oldest lines are dropped.
"""

import os
import sys
import logging

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ---------------------------------------------------------------------------
# File-based logging so backend debug messages are preserved between redraws
# ---------------------------------------------------------------------------
try:
    log_name = os.path.splitext(os.path.basename(__file__))[0] + '.log'
    fh = logging.FileHandler(log_name, mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s %(name)s %(levelname)s: %(message)s'))
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    _already = any(
        isinstance(h, logging.FileHandler) and
        os.path.abspath(getattr(h, 'baseFilename', '')) == os.path.abspath(log_name)
        for h in root_logger.handlers
    )
    if not _already:
        root_logger.addHandler(fh)
    print(f"Logging to: {os.path.abspath(log_name)}")
except Exception as _le:
    print(f"Warning: could not configure file logger: {_le}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
INITIAL_LINES = 40   # number of lines pre-loaded into each view
APPEND_BATCH  = 10   # lines added per "Append" button press
STORED_LINES  = 60   # ring-buffer depth per view


def _make_block(prefix: str, start: int, count: int) -> str:
    """Return *count* numbered log lines beginning at *start*."""
    return "\n".join(
        f"[{prefix}] line {start + i:04d}  " + "-" * ((start + i) % 30)
        for i in range(count)
    )


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------
def test_logview(backend_name: str | None = None):
    """Open an interactive dialog exercising all focus/reverse combinations."""
    if backend_name:
        print(f"Setting backend to: {backend_name}")
        os.environ['MUI_BACKEND'] = backend_name
    else:
        print("Using auto-detection")

    try:
        from manatools.aui.yui import YUI, YUI_ui, YLogViewFocus
        import manatools.aui.yui_common as yui

        # Force re-detection so repeated calls work
        YUI._instance = None
        YUI._backend  = None

        backend = YUI.backend()
        print(f"Using backend: {backend.value}")

        ui      = YUI_ui()
        factory = ui.widgetFactory()
        dialog  = factory.createMainDialog()

        outer = factory.createVBox(dialog)
        factory.createHeading(outer, f"YLogView focus/reverse test — {backend.value}")
        factory.createLabel(
            outer,
            "Left col = HEAD focus  |  Right col = TAIL focus  "
            "(top row = normal order, bottom row = reverse order)")

        # -----------------------------------------------------------------------
        # Two-column layout: left = HEAD views, right = TAIL views
        # -----------------------------------------------------------------------
        cols = factory.createHBox(outer)
        left_col  = factory.createVBox(cols)
        right_col = factory.createVBox(cols)

        # --- Case 1: HEAD / normal -------------------------------------------
        # display: oldest at top, newest at bottom; viewport stays at TOP (oldest)
        lv_head_norm = factory.createLogView(
            left_col,
            "Case 1 — HEAD/normal: top=oldest, viewport at TOP (no auto-scroll)",
            12, STORED_LINES,
            focus=YLogViewFocus.HEAD, reverse=False)
        lv_head_norm.appendLines(_make_block("HN", 1, INITIAL_LINES))

        # --- Case 2: HEAD / reverse ------------------------------------------
        # display: newest at top, oldest at bottom; viewport stays at TOP (newest)
        lv_head_rev = factory.createLogView(
            left_col,
            "Case 2 — HEAD/reverse: top=newest, viewport at TOP (newest always visible)",
            12, STORED_LINES,
            focus=YLogViewFocus.HEAD, reverse=True)
        lv_head_rev.appendLines(_make_block("HR", 1, INITIAL_LINES))

        # --- Case 3: TAIL / normal -------------------------------------------
        # display: oldest at top, newest at bottom; viewport auto-scrolls to BOTTOM
        lv_tail_norm = factory.createLogView(
            right_col,
            "Case 3 — TAIL/normal: top=oldest, viewport auto-scrolls to BOTTOM (newest)",
            12, STORED_LINES,
            focus=YLogViewFocus.TAIL, reverse=False)
        lv_tail_norm.appendLines(_make_block("TN", 1, INITIAL_LINES))

        # --- Case 4: TAIL / reverse ------------------------------------------
        # display: newest at top, oldest at bottom; viewport auto-scrolls to BOTTOM (oldest)
        # Opposite of case 1: case 1 = viewport at top/oldest; case 4 = viewport at bottom/oldest
        lv_tail_rev = factory.createLogView(
            right_col,
            "Case 4 — TAIL/reverse: top=newest, viewport auto-scrolls to BOTTOM (oldest)",
            12, STORED_LINES,
            focus=YLogViewFocus.TAIL, reverse=True)
        lv_tail_rev.appendLines(_make_block("TR", 1, INITIAL_LINES))

        all_views = [
            (lv_head_norm, "HN"),
            (lv_head_rev,  "HR"),
            (lv_tail_norm, "TN"),
            (lv_tail_rev,  "TR"),
        ]

        # -----------------------------------------------------------------------
        # Buttons
        # -----------------------------------------------------------------------
        btn_row = factory.createHBox(outer)
        append_btn = factory.createPushButton(btn_row, "Append 10 lines (all)")
        clear_btn  = factory.createPushButton(btn_row, "Clear (all)")
        toggle_focus_btn  = factory.createPushButton(btn_row, "Toggle focus (right col)")
        toggle_rev_btn    = factory.createPushButton(btn_row, "Toggle reverse (right col)")
        close_btn  = factory.createPushButton(btn_row, "Close")

        print("\nDialog open. Expected behaviour per case:")
        print("  Case 1 HEAD/normal  : viewport stays at TOP   = oldest line (no auto-scroll)")
        print("  Case 2 HEAD/reverse : viewport stays at TOP   = newest line (no auto-scroll needed)")
        print("  Case 3 TAIL/normal  : viewport auto-scrolls to BOTTOM = newest line")
        print("  Case 4 TAIL/reverse : viewport auto-scrolls to BOTTOM = oldest line (opposite of case 1)")
        print(f"  storedLines={STORED_LINES}: buffer trims oldest lines once exceeded")
        print("  _lines is ALWAYS in chronological order internally")

        counter = INITIAL_LINES + 1  # next line number

        while True:
            ev = dialog.waitForEvent()
            et = ev.eventType()

            if et == yui.YEventType.CancelEvent:
                break

            elif et == yui.YEventType.WidgetEvent:
                wdg    = ev.widget()
                reason = ev.reason()

                if reason != yui.YEventReason.Activated:
                    continue

                if wdg == close_btn:
                    break

                elif wdg == clear_btn:
                    for lv, _ in all_views:
                        lv.clearText()
                    counter = 1
                    print("Cleared all views, counter reset to 1.")

                elif wdg == append_btn:
                    for lv, prefix in all_views:
                        lv.appendLines(_make_block(prefix, counter, APPEND_BATCH))
                    counter += APPEND_BATCH
                    print(f"Appended lines {counter - APPEND_BATCH}–{counter - 1} to all views.")

                elif wdg == toggle_focus_btn:
                    for lv, _ in (all_views[2], all_views[3]):  # right col
                        new_f = (
                            YLogViewFocus.HEAD
                            if lv.focus() == YLogViewFocus.TAIL
                            else YLogViewFocus.TAIL
                        )
                        lv.setFocus(new_f)
                    print(f"Right-col focus is now: {lv_tail_norm.focus().name}")

                elif wdg == toggle_rev_btn:
                    for lv, _ in (all_views[2], all_views[3]):  # right col
                        lv.setReverse(not lv.reverse())
                    print(
                        f"Right-col reverse is now: {lv_tail_norm.reverse()}  "
                        "(internal _lines buffer unchanged)")

        dialog.destroy()

    except Exception as exc:
        print(f"Error: {exc}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            ui.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_logview(sys.argv[1])
    else:
        test_logview()

