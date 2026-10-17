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
        super().__init__(parent, html)
        self._logger = logging.getLogger(f"manatools.aui.ncurses.{self.__class__.__name__}")
        self._apply_content()

    def _apply_content(self):
        # Feed the flattened content to the YRichText parser (rich mode),
        # bypassing YHtmlViewBase.setValue() which means setHtml() here.
        self._plain = False
        YRichTextCurses.setValue(self, self._text_simple_html())

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
