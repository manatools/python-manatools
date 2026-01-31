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
from html.parser import HTMLParser
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
        self._heading_lines = set()
        self._color_link = None
        self._color_link_armed = None
        self._parsed_lines = None
        self._named_color_pairs = {}
        self._next_color_pid = 20
        #tooltip support
        self._x = 0
        self._y = 0
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
            # initial parse for rich mode
            if not self._plain:
                try:
                    self._anchors = self._parse_anchors(self._text)
                    self._anchors.sort(key=lambda a: (a['sline'], a['scol']))
                except Exception:
                    self._anchors = []
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
                self._anchors.sort(key=lambda a: (a['sline'], a['scol']))
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
            # anchors: keep inner text only; URLs handled via anchor list
            t = re.sub(r"<a\s+[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"\2", t, flags=re.IGNORECASE|re.DOTALL)
            t = re.sub(r"<a\s+[^>]*href='([^']+)'[^>]*>(.*?)</a>", r"\2", t, flags=re.IGNORECASE|re.DOTALL)
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
        # New parser-based implementation
        anchors = []
        try:
            class Parser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.lines = [[]]
                    self.styles = []
                    self.anchor = None
                    self.buf = ""
                    self.heading_lines = set()

                def _flush(self):
                    if not self.buf:
                        return
                    seg = {
                        'text': self.buf,
                        'bold': any(s == 'b' for s in self.styles),
                        'italic': any(s == 'i' for s in self.styles),
                        'underline': any(s == 'u' for s in self.styles) or (self.anchor is not None),
                        'color': None,
                        'anchor': self.anchor
                    }
                    for s in self.styles:
                        if isinstance(s, dict) and 'color' in s:
                            seg['color'] = s['color']
                    self.lines[-1].append(seg)
                    self.buf = ""

                def handle_starttag(self, tag, attrs):
                    at = dict(attrs)
                    if tag == 'br':
                        self._flush()
                        self.lines.append([])
                    elif tag == 'p':
                        self._flush()
                        self.lines.append([])
                    elif tag in ('ul','ol'):
                        self._flush()
                        self.lines.append([])
                    elif tag == 'li':
                        self._flush()
                        self.buf += '• '
                    elif tag in ('h1','h2','h3','h4','h5','h6'):
                        # flush previous text, then mark heading as bold
                        self._flush()
                        self.styles.append('b')
                    elif tag == 'a':
                        href = at.get('href') or at.get('HREF')
                        self._flush()
                        self.anchor = href
                    elif tag == 'span':
                        # flush previous text, then push color/style
                        self._flush()
                        color = at.get('foreground') or None
                        if not color and 'style' in at:
                            m = re.search(r'color:\s*([^;]+)', at.get('style'))
                            if m:
                                color = m.group(1)
                        if color:
                            self.styles.append({'color': color})
                        else:
                            self.styles.append('span')
                    elif tag == 'b':
                        self._flush()
                        self.styles.append('b')
                    elif tag in ('i','em'):
                        self._flush()
                        self.styles.append('i')
                    elif tag == 'u':
                        self._flush()
                        self.styles.append('u')

                def handle_endtag(self, tag):
                    if tag == 'br':
                        self._flush()
                        self.lines.append([])
                    elif tag == 'p':
                        self._flush()
                        self.lines.append([])
                    elif tag in ('ul','ol'):
                        self._flush()
                        self.lines.append([])
                    elif tag == 'li':
                        self._flush()
                        self.lines.append([])
                    elif tag in ('h1','h2','h3','h4','h5','h6'):
                        try:
                            self.styles.remove('b')
                        except ValueError:
                            pass
                        self._flush()
                        # mark current line as heading
                        try:
                            self.heading_lines.add(len(self.lines)-1)
                        except Exception:
                            pass
                        self.lines.append([])
                    elif tag == 'a':
                        self._flush()
                        self.anchor = None
                    elif tag == 'span':
                        # pop last color dict if present
                        for i in range(len(self.styles)-1, -1, -1):
                            if isinstance(self.styles[i], dict) and 'color' in self.styles[i]:
                                del self.styles[i]
                                break
                        else:
                            if self.styles:
                                self.styles.pop()
                        self._flush()
                    elif tag == 'b':
                        try:
                            self.styles.remove('b')
                        except ValueError:
                            pass
                        self._flush()
                    elif tag in ('i','em'):
                        try:
                            self.styles.remove('i')
                        except ValueError:
                            pass
                        self._flush()
                    elif tag == 'u':
                        try:
                            self.styles.remove('u')
                        except ValueError:
                            pass
                        self._flush()

                def handle_data(self, data):
                    parts = data.split('\n')
                    for idx, part in enumerate(parts):
                        if idx > 0:
                            self._flush()
                            self.lines.append([])
                        self.buf += part

            p = Parser()
            p.feed(s)
            p._flush()
            lines = p.lines
            # collect anchors and heading lines from parser
            anchors = []
            self._heading_lines = set(p.heading_lines)
            for ln_idx, segs in enumerate(lines):
                col = 0
                for seg_idx, seg in enumerate(segs):
                    text = seg.get('text','')
                    length = len(text)
                    if seg.get('anchor'):
                        anchors.append({'sline': ln_idx, 'scol': col, 'eline': ln_idx, 'ecol': col + length, 'target': seg.get('anchor'), 'seg_idx': seg_idx})
                    col += length
            self._parsed_lines = lines
        except Exception:
            self._parsed_lines = None
            anchors = []
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
        if self._visible is False:
            return
        try:
            # draw border
            try:
                window.attrset(curses.A_NORMAL)
                window.border()
            except curses.error:
                pass

            inner_x = x + 1
            inner_y = y + 1
            self._x = inner_x
            self._y = inner_y
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
            # remember for visibility calculations
            self._last_content_w = content_w
            self._last_width = width

            # draw content with horizontal scrolling
            segmented = bool(lines and isinstance(lines[0], list))
            for i in range(visible):
                idx = self._scroll_offset + i
                if idx >= total_rows:
                    break
                attr_default = curses.A_NORMAL
                if not self.isEnabled():
                    attr_default |= curses.A_DIM
                # apply heading style when applicable
                is_heading = (not self._plain) and (idx in getattr(self, '_heading_lines', set()))
                if is_heading:
                    attr_default |= curses.A_BOLD
                # highlight hover line only in plain mode or without anchors
                if (self._plain or not self._anchors) and self._focused and idx == self._hover_line and self.isEnabled():
                    attr_default |= curses.A_REVERSE

                start_col = self._hscroll_offset
                end_col = self._hscroll_offset + content_w

                try:
                    line_x = inner_x
                    if not segmented:
                        txt = lines[idx]
                        segment = txt[start_col:end_col]
                        if is_heading:
                            # bold + red for headings
                            a = attr_default
                            red_pid = self._get_named_color_pair('red')
                            if red_pid is not None:
                                try:
                                    a |= curses.color_pair(red_pid)
                                except Exception:
                                    pass
                            window.addstr(inner_y + i, inner_x, segment.ljust(content_w), a)
                        else:
                            window.addstr(inner_y + i, inner_x, segment.ljust(content_w), attr_default)
                    else:
                        segs = lines[idx]
                        # iterate segments and draw visible portion
                        char_cursor = 0
                        for seg in segs:
                            text = seg.get('text', '')
                            if not text:
                                continue
                            seg_len = len(text)
                            seg_start = char_cursor
                            seg_end = char_cursor + seg_len
                            # no overlap with visible window?
                            if seg_end <= start_col:
                                char_cursor += seg_len
                                continue
                            if seg_start >= end_col:
                                break
                            # compute visible slice within this segment
                            vis_lo = max(start_col, seg_start) - seg_start
                            vis_hi = min(end_col, seg_end) - seg_start
                            piece = text[vis_lo:vis_hi]
                            if not piece:
                                char_cursor += seg_len
                                continue
                            # determine attributes for this piece
                            a = attr_default
                            if is_heading:
                                # headings: bold + red
                                red_pid = self._get_named_color_pair('red')
                                if red_pid is not None:
                                    try:
                                        a |= curses.color_pair(red_pid)
                                    except Exception:
                                        pass
                            else:
                                # unify bold/italic/underline and anchors to bold gray
                                if seg.get('bold') or seg.get('italic') or seg.get('underline') or seg.get('anchor'):
                                    a |= curses.A_BOLD
                                    gray_pid = self._get_named_color_pair('gray')
                                    if gray_pid is not None:
                                        try:
                                            a |= curses.color_pair(gray_pid)
                                        except Exception:
                                            pass
                                else:
                                    # optional explicit color spans for normal text
                                    self._ensure_color_pairs()
                                    color_id = None
                                    if isinstance(seg.get('color'), int):
                                        color_id = seg.get('color')
                                    elif seg.get('color'):
                                        color_id = self._get_named_color_pair(seg.get('color'))
                                    if color_id is not None:
                                        try:
                                            a |= curses.color_pair(color_id)
                                        except Exception:
                                            pass
                                # armed anchor: add reverse for visibility
                                if seg.get('anchor') and self._armed_index != -1 and 0 <= self._armed_index < len(self._anchors):
                                    a_active = self._anchors[self._armed_index]
                                    if a_active and a_active['sline'] == idx and a_active['scol'] <= seg_start and a_active['ecol'] >= seg_end:
                                        a |= curses.A_REVERSE

                            try:
                                window.addstr(inner_y + i, line_x, piece, a)
                            except curses.error:
                                pass
                            line_x += len(piece)
                            char_cursor += seg_len
                        # pad remainder
                        rem = content_w - (line_x - inner_x)
                        if rem > 0:
                            try:
                                window.addstr(inner_y + i, line_x, " " * rem, attr_default)
                            except curses.error:
                                pass
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
                    if total_rows > visible:
                        pos = int((self._scroll_offset / max(1, total_rows - visible)) * (content_h - 1))
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
                        hpos = int((self._hscroll_offset / max(1, maxlen - content_w)) * (content_w - 1))
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
        lines = self._parsed_lines if (not self._plain and getattr(self, '_parsed_lines', None)) else self._lines()
        if key == curses.KEY_UP:
            if self._anchors:
                if self._armed_index > 0:
                    self._armed_index -= 1
                    a = self._anchors[self._armed_index]
                    self._hover_line = a['sline']
                    self._ensure_anchor_visible(a)
                else:
                    if self._hover_line > 0:
                        self._hover_line -= 1
                        self._ensure_hover_visible()
        elif key == curses.KEY_DOWN:
            if self._anchors:
                if self._armed_index + 1 < len(self._anchors):
                    self._armed_index += 1
                    a = self._anchors[self._armed_index]
                    self._hover_line = a['sline']
                    self._ensure_anchor_visible(a)
                else:
                    if self._hover_line < max(0, len(lines) - 1):
                        self._hover_line += 1
                        self._ensure_hover_visible()
        elif key == curses.KEY_LEFT:
            # horizontal scroll or move to previous anchor
            if self._anchors:
                if self._armed_index > 0:
                    self._armed_index -= 1
                    a = self._anchors[self._armed_index]
                    self._hover_line = a['sline']
                    self._ensure_anchor_visible(a)
            else:
                if self._hscroll_offset > 0:
                    self._hscroll_offset = max(0, self._hscroll_offset - max(1, (self._visible_row_count() // 2)))
        elif key == curses.KEY_RIGHT:
            if self._anchors:
                if self._armed_index + 1 < len(self._anchors):
                    self._armed_index += 1
                    a = self._anchors[self._armed_index]
                    self._hover_line = a['sline']
                    self._ensure_anchor_visible(a)
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
                if self._anchors and self._armed_index != -1 and 0 <= self._armed_index < len(self._anchors):
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
                self._ensure_anchor_visible(self._anchors[0])

    def _ensure_anchor_visible(self, a):
        try:
            # vertical
            self._hover_line = a['sline']
            self._ensure_hover_visible()
            # horizontal: use last known content width
            visible_w = max(1, getattr(self, '_last_content_w', 0))
            if visible_w <= 0:
                visible_w = 40
            start_col = self._hscroll_offset
            end_col = start_col + visible_w
            if a['scol'] < start_col:
                self._hscroll_offset = max(0, a['scol'])
            elif a['ecol'] > end_col:
                self._hscroll_offset = max(0, a['ecol'] - visible_w)
        except Exception:
            pass

    def _ensure_color_pairs(self):
        try:
            if self._color_link is not None and self._color_link_armed is not None:
                return
            if curses.has_colors():
                try:
                    curses.start_color()
                    # prefer default background where supported
                    if hasattr(curses, 'use_default_colors'):
                        try:
                            curses.use_default_colors()
                        except Exception:
                            pass
                except Exception:
                    pass
                pid_link = 10
                pid_link_armed = 11
                try:
                    curses.init_pair(pid_link, curses.COLOR_BLUE, -1)
                    self._color_link = pid_link
                except Exception:
                    self._color_link = None
                try:
                    curses.init_pair(pid_link_armed, curses.COLOR_CYAN, -1)
                    self._color_link_armed = pid_link_armed
                except Exception:
                    self._color_link_armed = None
        except Exception:
            pass

    def _get_named_color_pair(self, name: str):
        try:
            if not name:
                return None
            if not curses.has_colors():
                return None
            # normalize name
            nm = str(name).strip().lower()
            # map common color names
            cmap = {
                'black': curses.COLOR_BLACK,
                'red': curses.COLOR_RED,
                'green': curses.COLOR_GREEN,
                'yellow': curses.COLOR_YELLOW,
                'blue': curses.COLOR_BLUE,
                'magenta': curses.COLOR_MAGENTA,
                'purple': curses.COLOR_MAGENTA,
                'cyan': curses.COLOR_CYAN,
                'white': curses.COLOR_WHITE,
                'gray': curses.COLOR_WHITE,
                'grey': curses.COLOR_WHITE,
            }
            fg = cmap.get(nm)
            if fg is None:
                return None
            # reuse if exists
            if nm in self._named_color_pairs:
                return self._named_color_pairs[nm]
            # init colors if needed
            try:
                curses.start_color()
                if hasattr(curses, 'use_default_colors'):
                    curses.use_default_colors()
            except Exception:
                pass
            pid = self._next_color_pid
            # advance, avoid collisions with link pairs
            self._next_color_pid = pid + 1
            try:
                curses.init_pair(pid, fg, -1)
                self._named_color_pairs[nm] = pid
                return pid
            except Exception:
                return None
        except Exception:
            return None

