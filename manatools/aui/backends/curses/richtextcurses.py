# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Curses backend RichText widget.
- Displays text content in a scrollable area.
- In plain text mode, shows the text as-is.
- In rich mode, strips simple HTML tags for display; detects URLs.
- Link activation: pressing Enter on a line with a URL posts a YMenuEvent with the URL.
'''
import curses
import re
import logging
from ...yui_common import *

_mod_logger = logging.getLogger("manatools.aui.curses.richtext.module")
if not logging.getLogger().handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    _mod_logger.addHandler(_h)
    _mod_logger.setLevel(logging.INFO)


class YRichTextCurses(YWidget):
    def __init__(self, parent=None, text: str = "", plainTextMode: bool = False):
        super().__init__(parent)
        self._text = text or ""
        self._plain = bool(plainTextMode)
        self._auto_scroll = False
        self._last_url = None
        self._height = 6
        self._can_focus = True
        self._focused = False
        self._scroll_offset = 0  # vertical offset
        self._hscroll_offset = 0  # horizontal offset
        self._hover_line = 0
        self._anchors = []  # list of dicts: {sline, scol, eline, ecol, target}
        self._armed_index = -1
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        if not self._logger.handlers and not logging.getLogger().handlers:
            for h in _mod_logger.handlers:
                self._logger.addHandler(h)

    def widgetClass(self):
        return "YRichText"

    def _create_backend_widget(self):
        try:
            self._backend_widget = self
            self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())
        except Exception as e:
            try:
                self._logger.error("_create_backend_widget error: %s", e, exc_info=True)
            except Exception:
                _mod_logger.error("_create_backend_widget error: %s", e, exc_info=True)

    def setValue(self, newValue: str):
        self._text = newValue or ""
        # re-parse anchors when in rich mode
        if not self._plain:
            try:
                self._anchors = self._parse_anchors(self._text)
            except Exception:
                self._anchors = []
        # autoscroll: move hover to last line
        if self._auto_scroll:
            lines = self._lines()
            self._hover_line = max(0, len(lines) - 1)
            self._ensure_hover_visible()

    def value(self) -> str:
        return self._text

    def plainTextMode(self) -> bool:
        return bool(self._plain)

    def setPlainTextMode(self, on: bool = True):
        self._plain = bool(on)

    def autoScrollDown(self) -> bool:
        return bool(self._auto_scroll)

    def setAutoScrollDown(self, on: bool = True):
        self._auto_scroll = bool(on)
        if self._auto_scroll:
            lines = self._lines()
            self._hover_line = max(0, len(lines) - 1)
            self._ensure_hover_visible()

    def lastActivatedUrl(self):
        return self._last_url

    def _strip_tags(self, s: str) -> str:
        # Convert minimal HTML into text breaks and bullets, then strip remaining tags
        try:
            t = s
            # breaks and paragraphs
            t = re.sub(r"<br\s*/?>", "\n", t, flags=re.IGNORECASE)
            t = re.sub(r"</p\s*>", "\n\n", t, flags=re.IGNORECASE)
            t = re.sub(r"<p\s*>", "", t, flags=re.IGNORECASE)
            # lists
            t = re.sub(r"<ul\s*>", "\n", t, flags=re.IGNORECASE)
            t = re.sub(r"</ul\s*>", "\n", t, flags=re.IGNORECASE)
            t = re.sub(r"<ol\s*>", "\n", t, flags=re.IGNORECASE)
            t = re.sub(r"</ol\s*>", "\n", t, flags=re.IGNORECASE)
            t = re.sub(r"<li\s*>", "• ", t, flags=re.IGNORECASE)
            t = re.sub(r"</li\s*>", "\n", t, flags=re.IGNORECASE)
            # headings -> uppercase with newline
            for n in range(1,7):
                t = re.sub(fr"<h{n}\s*>", "", t, flags=re.IGNORECASE)
                t = re.sub(fr"</h{n}\s*>", "\n", t, flags=re.IGNORECASE)
            # anchors: keep inner text and preserve URL text if no inner
            t = re.sub(r"<a\s+[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"\2 (\1)", t, flags=re.IGNORECASE|re.DOTALL)
            t = re.sub(r"<a\s+[^>]*href='([^']+)'[^>]*>(.*?)</a>", r"\2 (\1)", t, flags=re.IGNORECASE|re.DOTALL)
            return re.sub(r"<[^>]+>", "", t)
        except Exception:
            return s

    def _lines(self):
        content = self._text
        if not self._plain:
            content = self._strip_tags(content)
        lines = content.splitlines() or [""]
        return lines

    def _parse_anchors(self, s: str):
        """Parse <a href> anchors into line/column positions and targets.
        Returns a list of anchors with screen-relative positions based on current text conversion.
        """
        anchors = []
        try:
            # Build a text version while tracking anchors
            text = s
            # Normalize breaks the same way as in _strip_tags
            text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
            text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
            text = re.sub(r"<p\s*>", "", text, flags=re.IGNORECASE)
            text = re.sub(r"<ul\s*>", "\n", text, flags=re.IGNORECASE)
            text = re.sub(r"</ul\s*>", "\n", text, flags=re.IGNORECASE)
            text = re.sub(r"<ol\s*>", "\n", text, flags=re.IGNORECASE)
            text = re.sub(r"</ol\s*>", "\n", text, flags=re.IGNORECASE)
            text = re.sub(r"<li\s*>", "• ", text, flags=re.IGNORECASE)
            text = re.sub(r"</li\s*>", "\n", text, flags=re.IGNORECASE)
            # Find anchors and replace with inner text while recording positions
            pos = 0
            lines = []
            current_line = ""
            for m in re.finditer(r"<a\s+[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>|<a\s+[^>]*href='([^']+)'[^>]*>(.*?)</a>|<br\s*/?>|</p\s*>|<p\s*>|</?ul\s*>|</?ol\s*>|<li\s*>|</li\s*>", text, flags=re.IGNORECASE|re.DOTALL):
                start, end = m.span()
                # Add text before match
                before = re.sub(r"<[^>]+>", "", text[pos:start])
                for ch in before:
                    if ch == '\n':
                        lines.append(current_line)
                        current_line = ""
                    else:
                        current_line += ch
                if m.group(1) is not None:
                    url = m.group(1)
                    inner = m.group(2) or url
                    sline = len(lines)
                    scol = len(current_line)
                    current_line += inner
                    eline = len(lines)
                    ecol = len(current_line)
                    anchors.append({"sline": sline, "scol": scol, "eline": eline, "ecol": ecol, "target": url})
                elif m.group(3) is not None:
                    url = m.group(3)
                    inner = m.group(4) or url
                    sline = len(lines)
                    scol = len(current_line)
                    current_line += inner
                    eline = len(lines)
                    ecol = len(current_line)
                    anchors.append({"sline": sline, "scol": scol, "eline": eline, "ecol": ecol, "target": url})
                else:
                    tagtxt = text[start:end]
                    # handle structural tags resulting in newlines/bullets
                    if re.match(r"<br\s*/?>", tagtxt, flags=re.IGNORECASE):
                        lines.append(current_line)
                        current_line = ""
                    elif re.match(r"</p\s*>", tagtxt, flags=re.IGNORECASE):
                        lines.append(current_line)
                        lines.append("")
                        current_line = ""
                    elif re.match(r"<p\s*>", tagtxt, flags=re.IGNORECASE):
                        pass
                    elif re.match(r"<ul\s*>|<ol\s*>", tagtxt, flags=re.IGNORECASE):
                        lines.append(current_line)
                        current_line = ""
                    elif re.match(r"</ul\s*>|</ol\s*>", tagtxt, flags=re.IGNORECASE):
                        lines.append(current_line)
                        current_line = ""
                    elif re.match(r"<li\s*>", tagtxt, flags=re.IGNORECASE):
                        current_line += "• "
                    elif re.match(r"</li\s*>", tagtxt, flags=re.IGNORECASE):
                        lines.append(current_line)
                        current_line = ""
                pos = end
            # trailing text
            trailing = re.sub(r"<[^>]+>", "", text[pos:])
            for ch in trailing:
                if ch == '\n':
                    lines.append(current_line)
                    current_line = ""
                else:
                    current_line += ch
            lines.append(current_line)
            # store parsed lines for rendering
            self._parsed_lines = lines
        except Exception:
            self._parsed_lines = None
        return anchors

    def _visible_row_count(self):
        return max(1, getattr(self, "_preferred_rows", 6))

    def _ensure_hover_visible(self):
        visible = self._visible_row_count()
        if self._hover_line < self._scroll_offset:
            self._scroll_offset = self._hover_line
        elif self._hover_line >= self._scroll_offset + visible:
            self._scroll_offset = self._hover_line - visible + 1

    def _draw(self, window, y, x, width, height):
        try:
            # draw border
            try:
                window.attrset(curses.A_NORMAL)
                window.border()
            except curses.error:
                pass

            inner_x = x + 1
            inner_y = y + 1
            inner_w = max(1, width - 2)
            inner_h = max(1, height - 2)

            # reserve rightmost column for vertical scrollbar, bottom row for horizontal scrollbar
            bar_w = 1 if inner_w > 2 else 0
            content_w = inner_w - bar_w
            bar_h_row = 1 if inner_h > 2 else 0
            content_h = inner_h - bar_h_row

            # obtain lines (prefer parsed rich lines if available)
            lines = self._parsed_lines if (not self._plain and getattr(self, '_parsed_lines', None)) else self._lines()
            total_rows = len(lines)
            visible = min(total_rows, max(1, content_h))

            # draw content with horizontal scrolling
            for i in range(visible):
                idx = self._scroll_offset + i
                if idx >= total_rows:
                    break
                txt = lines[idx]
                # horizontal slice
                start_col = self._hscroll_offset
                end_col = self._hscroll_offset + content_w
                segment = txt[start_col:end_col]
                attr_default = curses.A_NORMAL
                if not self.isEnabled():
                    attr_default |= curses.A_DIM
                # highlight hover line background
                if self._focused and idx == self._hover_line and self.isEnabled():
                    attr_default |= curses.A_REVERSE
                # draw with anchor highlighting (underline)
                try:
                    # build segments around anchors
                    line_x = inner_x
                    consumed = 0
                    # anchors on this line
                    alist = [a for a in self._anchors if a['sline'] == idx]
                    if not alist:
                        window.addstr(inner_y + i, inner_x, segment.ljust(content_w), attr_default)
                    else:
                        # draw piecewise
                        cursor = start_col
                        for a in alist:
                            a_start = a['scol']
                            a_end = a['ecol']
                            # draw text before anchor
                            if a_start > cursor:
                                pre = txt[cursor:min(a_start, end_col)]
                                if pre:
                                    window.addstr(inner_y + i, line_x, pre, attr_default)
                                    line_x += len(pre)
                                    cursor += len(pre)
                            # draw anchor segment
                            if a_end > cursor and cursor < end_col:
                                anc_seg = txt[max(cursor, a_start):min(a_end, end_col)]
                                if anc_seg:
                                    attr_anchor = attr_default | curses.A_UNDERLINE
                                    # extra highlight if armed
                                    if self._armed_index != -1 and self._anchors[self._armed_index] is a:
                                        attr_anchor |= curses.A_BOLD
                                    window.addstr(inner_y + i, line_x, anc_seg, attr_anchor)
                                    line_x += len(anc_seg)
                                    cursor += len(anc_seg)
                        # draw trailing text
                        if cursor < end_col:
                            tail = txt[cursor:end_col]
                            if tail:
                                window.addstr(inner_y + i, line_x, tail, attr_default)
                        # pad remainder
                        rem = content_w - (line_x - inner_x)
                        if rem > 0:
                            window.addstr(inner_y + i, line_x, " " * rem, attr_default)
                except curses.error:
                    pass

            # vertical scrollbar on right
            if bar_w == 1 and content_h > 0 and total_rows > visible:
                try:
                    # draw track
                    for r in range(content_h):
                        window.addch(inner_y + r, inner_x + content_w, '|')
                    # draw slider position
                    pos = 0
                    if total_rows > 0:
                        pos = int((self._scroll_offset / max(1, total_rows)) * content_h)
                    pos = max(0, min(content_h - 1, pos))
                    window.addch(inner_y + pos, inner_x + content_w, '#')
                except curses.error:
                    pass

            # horizontal scrollbar on bottom
            if bar_h_row == 1:
                try:
                    # basic track
                    for c in range(content_w):
                        window.addch(inner_y + content_h, inner_x + c, '-')
                    # slider position relative to max line length
                    maxlen = max((len(l) for l in lines), default=0)
                    if maxlen > content_w:
                        hpos = int((self._hscroll_offset / max(1, maxlen - content_w)) * content_w)
                        hpos = max(0, min(content_w - 1, hpos))
                        window.addch(inner_y + content_h, inner_x + hpos, '=')
                except curses.error:
                    pass
        except curses.error:
            pass

    def _handle_key(self, key):
        if not self._focused or not self.isEnabled():
            return False
        handled = True
        lines = self._lines()
        if key == curses.KEY_UP:
            if self._hover_line > 0:
                self._hover_line -= 1
                self._ensure_hover_visible()
        elif key == curses.KEY_DOWN:
            if self._hover_line < max(0, len(lines) - 1):
                self._hover_line += 1
                self._ensure_hover_visible()
        elif key == curses.KEY_LEFT:
            # horizontal scroll or move to previous anchor
            if self._armed_index != -1:
                if self._armed_index > 0:
                    self._armed_index -= 1
                    a = self._anchors[self._armed_index]
                    self._hover_line = a['sline']
                    self._ensure_hover_visible()
            else:
                if self._hscroll_offset > 0:
                    self._hscroll_offset = max(0, self._hscroll_offset - max(1, (self._visible_row_count() // 2)))
        elif key == curses.KEY_RIGHT:
            if self._armed_index != -1:
                if self._armed_index + 1 < len(self._anchors):
                    self._armed_index += 1
                    a = self._anchors[self._armed_index]
                    self._hover_line = a['sline']
                    self._ensure_hover_visible()
            else:
                maxlen = max((len(l) for l in lines), default=0)
                if maxlen > self._hscroll_offset:
                    self._hscroll_offset = min(maxlen, self._hscroll_offset + max(1, (self._visible_row_count() // 2)))
        elif key == curses.KEY_PPAGE:
            step = self._visible_row_count() or 1
            self._hover_line = max(0, self._hover_line - step)
            self._ensure_hover_visible()
        elif key == curses.KEY_NPAGE:
            step = self._visible_row_count() or 1
            self._hover_line = min(max(0, len(lines) - 1), self._hover_line + step)
            self._ensure_hover_visible()
        elif key == curses.KEY_HOME:
            self._hover_line = 0
            self._ensure_hover_visible()
        elif key == curses.KEY_END:
            self._hover_line = max(0, len(lines) - 1)
            self._ensure_hover_visible()
        elif key in (ord('\n'),):
            # Try to detect a URL in the current line and emit a menu event
            try:
                if self._armed_index != -1 and 0 <= self._armed_index < len(self._anchors):
                    url = self._anchors[self._armed_index]['target']
                    self._last_url = url
                    if self.notify():
                        dlg = self.findDialog()
                        if dlg is not None:
                            dlg._post_event(YMenuEvent(item=None, id=url))
                else:
                    line = lines[self._hover_line] if 0 <= self._hover_line < len(lines) else ""
                    m = re.search(r"https?://\S+", line)
                    if m:
                        url = m.group(0)
                        self._last_url = url
                        if self.notify():
                            dlg = self.findDialog()
                            if dlg is not None:
                                dlg._post_event(YMenuEvent(item=None, id=url))
            except Exception:
                pass
        else:
            handled = False
        return handled

    def _set_backend_enabled(self, enabled):
        try:
            self._can_focus = bool(enabled)
            if not enabled:
                self._focused = False
        except Exception:
            pass

    # Focus handling hooks (optional integration with parent)
    def setFocus(self, on: bool = True):
        self._focused = bool(on) and self._can_focus
        # when focusing, if rich mode and anchors exist, arm first visible anchor
        if self._focused and not self._plain and self._anchors:
            # pick the first anchor within current page
            visible_top = self._scroll_offset
            visible_bottom = self._scroll_offset + (self._visible_row_count() or 1)
            for i, a in enumerate(self._anchors):
                if visible_top <= a['sline'] < visible_bottom:
                    self._armed_index = i
                    self._hover_line = a['sline']
                    break
            else:
                self._armed_index = 0
                self._hover_line = self._anchors[0]['sline']
