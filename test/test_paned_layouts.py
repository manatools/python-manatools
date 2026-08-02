#!/usr/bin/env python3
# vim: set fileencoding=utf-8 :
"""Phase 11 paned stabilization test case.

Builds three scenarios requested by dnfdragora validation:
1) vertical paned chain with >3 logical panes
2) horizontal paned chain with >3 logical panes
3) mixed vertical+horizontal nested paneds

Usage examples:
  MUI_BACKEND=qt python test/test_paned_phase11_layouts.py
  MUI_BACKEND=gtk python test/test_paned_phase11_layouts.py
  MUI_BACKEND=ncurses python test/test_paned_phase11_layouts.py
"""

import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    log_name = os.path.splitext(os.path.basename(__file__))[0] + '.log'
    logFormatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s: %(message)s')
    root_logger = logging.getLogger()
    fileHandler = logging.FileHandler(log_name, mode='w')
    fileHandler.setFormatter(logFormatter)
    root_logger.addHandler(fileHandler)
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    root_logger.addHandler(consoleHandler)
    consoleHandler.setLevel(logging.INFO)
    root_logger.setLevel(logging.DEBUG)
except Exception as _e:
    logging.getLogger().exception("Failed to configure file logger: %s", _e)

def _mk_table(factory, parent, title, rows=6):
    import manatools.aui.yui_common as yui
    frame = factory.createFrame(parent, title)
    box = factory.createVBox(frame)
    header = yui.YTableHeader()
    header.addColumn("k")
    header.addColumn("v")
    table = factory.createTable(box, header)
    table.setStretchable(yui.YUIDimension.YD_HORIZ, True)
    table.setStretchable(yui.YUIDimension.YD_VERT, True)
    items = []
    for i in range(rows):
        item = yui.YTableItem()
        item.addCell(str(i))
        item.addCell(f"{title}-{i}")
        items.append(item)
    table.addItems(items)
    return frame, table


def test_paned_phase11_layouts(backend_name=None):
    if backend_name:
        os.environ['MUI_BACKEND'] = backend_name
        root_logger.info("Setting backend to: %s", backend_name)

    from manatools.aui.yui import YUI, YUI_ui
    import manatools.aui.yui_common as yui

    YUI._instance = None
    YUI._backend = None

    print(f"Using backend: {YUI.backend().value}")

    ui = YUI_ui()
    factory = ui.widgetFactory()
    dialog = factory.createMainDialog()
    minsize = factory.createMinSize(dialog, 1000, 700)
    root = factory.createVBox(minsize)

    title = factory.createHeading(root, "Phase11 Paned Stress Test")
    title.setAutoWrap()

    import manatools.aui.yui_common as yui

    tabs = factory.createDumbTab(root)
    tabs.setNotify(True)

    tab_names = ["Vertical>3", "Horizontal>3", "Mixed"]
    items = []
    for idx, name in enumerate(tab_names):
        it = yui.YItem(name, selected=(idx == 0))
        tabs.addItem(it)
        items.append(it)

    # DumbTab has a single child content area; switch scenarios through ReplacePoint.
    content = factory.createReplacePoint(tabs)

    def _render_vertical():
        page = factory.createVBox(content)
        p1 = factory.createPaned(page, yui.YUIDimension.YD_VERT)
        v4_frame, _v4_table = _mk_table(factory, p1, "V4")
        p2 = factory.createPaned(p1, yui.YUIDimension.YD_VERT)
        v3_frame, _v3_table = _mk_table(factory, p2, "V3")
        p3 = factory.createPaned(p2, yui.YUIDimension.YD_VERT)
        v2_frame, _v2_table = _mk_table(factory, p3, "V2")
        v1_frame, _v1_table = _mk_table(factory, p3, "V1")

        # Apply split ratios via references to direct paned children.
        v4_frame.setWeight(yui.YUIDimension.YD_VERT, 60)
        p2.setWeight(yui.YUIDimension.YD_VERT, 40)
        v3_frame.setWeight(yui.YUIDimension.YD_VERT, 60)
        p3.setWeight(yui.YUIDimension.YD_VERT, 40)
        v2_frame.setWeight(yui.YUIDimension.YD_VERT, 60)
        v1_frame.setWeight(yui.YUIDimension.YD_VERT, 40)

    def _render_horizontal():
        page = factory.createVBox(content)
        h1 = factory.createPaned(page, yui.YUIDimension.YD_HORIZ)
        h4_frame, _h4_table = _mk_table(factory, h1, "H4")
        h2 = factory.createPaned(h1, yui.YUIDimension.YD_HORIZ)
        h3_frame, _h3_table = _mk_table(factory, h2, "H3")
        h3 = factory.createPaned(h2, yui.YUIDimension.YD_HORIZ)
        h2_frame, _h2_table = _mk_table(factory, h3, "H2")
        h1_frame, _h1_table = _mk_table(factory, h3, "H1")

        h4_frame.setWeight(yui.YUIDimension.YD_HORIZ, 60)
        h2.setWeight(yui.YUIDimension.YD_HORIZ, 40)
        h3_frame.setWeight(yui.YUIDimension.YD_HORIZ, 60)
        h3.setWeight(yui.YUIDimension.YD_HORIZ, 40)
        h2_frame.setWeight(yui.YUIDimension.YD_HORIZ, 60)
        h1_frame.setWeight(yui.YUIDimension.YD_HORIZ, 40)

    def _render_mixed():
        page = factory.createVBox(content)
        m1 = factory.createPaned(page, yui.YUIDimension.YD_VERT)
        top = factory.createPaned(m1, yui.YUIDimension.YD_HORIZ)
        bot = factory.createPaned(m1, yui.YUIDimension.YD_HORIZ)
        m_top_l_frame, _m_top_l_table = _mk_table(factory, top, "M-Top-L")
        m_top_r_frame, _m_top_r_table = _mk_table(factory, top, "M-Top-R")
        m_bot_l_frame, _m_bot_l_table = _mk_table(factory, bot, "M-Bot-L")
        m_bot_r_frame, _m_bot_r_table = _mk_table(factory, bot, "M-Bot-R")

        top.setWeight(yui.YUIDimension.YD_VERT, 60)
        bot.setWeight(yui.YUIDimension.YD_VERT, 40)
        m_top_l_frame.setWeight(yui.YUIDimension.YD_HORIZ, 60)
        m_top_r_frame.setWeight(yui.YUIDimension.YD_HORIZ, 40)
        m_bot_l_frame.setWeight(yui.YUIDimension.YD_HORIZ, 60)
        m_bot_r_frame.setWeight(yui.YUIDimension.YD_HORIZ, 40)

    def _render_tab(index):
        try:
            content.deleteChildren()
        except Exception:
            pass
        if index == 0:
            _render_vertical()
        elif index == 1:
            _render_horizontal()
        else:
            _render_mixed()
        content.showChild()

    _render_tab(0)

    buttons = factory.createHBox(root)
    factory.createHStretch(buttons)
    close_btn = factory.createPushButton(buttons, "Close")

    while True:
        ev = dialog.waitForEvent()
        if not ev:
            continue
        et = ev.eventType()
        if et == yui.YEventType.CancelEvent:
            break
        if et == yui.YEventType.WidgetEvent:
            if ev.widget() == close_btn:
                break
            if ev.widget() == tabs and ev.reason() == yui.YEventReason.Activated:
                sel = tabs.selectedItem()
                idx = 0
                if sel is not None:
                    try:
                        idx = tab_names.index(sel.label())
                    except Exception:
                        idx = 0
                _render_tab(idx)

    dialog.destroy()


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    test_paned_phase11_layouts(arg)
