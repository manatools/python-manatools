# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Curses backend YHtmlView.

There is no HTML engine in a terminal: the sanitized content is flattened to
text (paragraphs, lists, quotes, table rows, emphasis) and displayed with the
YRichText curses machinery, which already provides scrolling and link
navigation.  Arrow keys move between links, Enter activates the armed one;
activation is reported like on every other backend (lastActivatedUrl() and a
YWidgetEvent with reason Activated), never by opening anything.

Unlike YRichText, which scrolls long lines sideways, lines are word-wrapped
to the widget width (re-wrapped whenever that width changes); link text is
kept on one row when it fits.

License: LGPLv2+

@package manatools.aui.backends.curses
'''
import curses
import logging
from ...yui_common import *
from .richtextcurses import YRichTextCurses


class YHtmlViewCurses(YHtmlViewBase, YRichTextCurses):
    """Read-only HTML view rendered as navigable text."""

    def __init__(self, parent=None, html: str = ""):
        # Attributes first: the YRichText parser runs during construction.
        self._raw_lines = None       # parsed lines before wrapping
        self._raw_headings = set()
        self._wrap_width = None      # width _parsed_lines is wrapped for
        self._wrap_origin = []       # wrapped row -> raw line index
        super().__init__(parent, html)
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        self._apply_content()

    def _apply_content(self):
        # Feed the flattened content to the YRichText parser (rich mode),
        # bypassing YHtmlViewBase.setValue() which means setHtml() here.
        self._plain = False
        YRichTextCurses.setValue(self, self._text_simple_html())

    # -- word wrapping ------------------------------------------------------

    def _parse_anchors(self, s: str):
        anchors = YRichTextCurses._parse_anchors(self, s)
        self._raw_lines = getattr(self, "_parsed_lines", None)
        self._raw_headings = set(getattr(self, "_heading_lines", set()))
        self._wrap_origin = list(range(len(self._raw_lines or [])))
        self._wrap_width = None
        return anchors

    def _draw(self, window, y, x, width, height):
        if self._raw_lines and width > 0 and width != self._wrap_width:
            self._rewrap(width)
        YRichTextCurses._draw(self, window, y, x, width, height)

    @staticmethod
    def _wrap_spans(text, width, keep):
        """(start, end) rows of *text* word-wrapped to *width*.  Spans in
        *keep* (link text no wider than a row) are never broken; the blanks
        a row is broken at are dropped."""
        def kept(i):
            return any(a < i < b for a, b in keep)

        rows, pos, n = [], 0, len(text)
        while n - pos > width:
            limit = pos + width
            cut = next((i for i in range(limit, pos, -1)
                        if text[i].isspace() and not kept(i)), None)
            if cut is None:
                # No blank to break at: hard break, but before kept text.
                cut = limit
                for a, b in keep:
                    if pos < a < cut < b:
                        cut = a
                end = cut
            else:
                end = cut
                while end > pos and text[end - 1].isspace():
                    end -= 1
            rows.append((pos, end))
            pos = cut
            while pos < n and text[pos].isspace():
                pos += 1
        if pos < n or not rows:
            rows.append((pos, n))
        return rows

    def _rewrap(self, width):
        old_origin = self._wrap_origin
        top = old_origin[self._scroll_offset] if 0 <= self._scroll_offset < len(old_origin) else 0
        hover = old_origin[self._hover_line] if 0 <= self._hover_line < len(old_origin) else 0

        lines, origin, first = [], [], {}
        for raw_idx, segs in enumerate(self._raw_lines):
            text = "".join(seg.get("text", "") for seg in segs)
            keep, col = [], 0
            for seg in segs:
                length = len(seg.get("text", ""))
                if seg.get("anchor") and length <= width:
                    keep.append((col, col + length))
                col += length
            first[raw_idx] = len(lines)
            for start, end in self._wrap_spans(text, width, keep):
                row, col = [], 0
                for seg in segs:
                    seg_text = seg.get("text", "")
                    lo, hi = max(start, col), min(end, col + len(seg_text))
                    if lo < hi:
                        piece = dict(seg)
                        piece["text"] = seg_text[lo - col:hi - col]
                        row.append(piece)
                    col += len(seg_text)
                lines.append(row)
                origin.append(raw_idx)

        anchors = []
        for ln_idx, segs in enumerate(lines):
            col = 0
            for seg_idx, seg in enumerate(segs):
                length = len(seg.get("text", ""))
                if seg.get("anchor"):
                    anchors.append({'sline': ln_idx, 'scol': col, 'eline': ln_idx,
                                    'ecol': col + length, 'target': seg.get("anchor"),
                                    'seg_idx': seg_idx})
                col += length

        self._parsed_lines = lines
        self._heading_lines = {i for i, raw in enumerate(origin) if raw in self._raw_headings}
        self._anchors = anchors
        self._wrap_origin = origin
        self._wrap_width = width
        self._hscroll_offset = 0
        self._scroll_offset = first.get(top, 0)
        self._hover_line = first.get(hover, 0)
        if self._armed_index >= len(anchors):
            self._armed_index = len(anchors) - 1
        if 0 <= self._armed_index < len(anchors):
            self._ensure_anchor_visible(anchors[self._armed_index])

    def _on_link(self, url: str):
        index = self._link_index(url)
        if index is not None:
            self._activate_link(index)

    def _handle_key(self, key):
        if key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
            if not self._focused or not self.isEnabled() or not self.visible():
                return False
            if self._anchors and 0 <= self._armed_index < len(self._anchors):
                self._on_link(self._anchors[self._armed_index]['target'])
            return True
        return super()._handle_key(key)
