# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Backend-independent HTML hardening for YHtmlView.

sanitize_html() turns untrusted HTML (typically a mail body) into a document
that is safe to hand to any rendering engine:

- no scripts, event handlers, frames, plugins, forms or SVG/MathML;
- no remote loads unless the caller allows them (blocked loads are counted so
  the application can offer a "show remote content" action);
- ``cid:`` references inlined as ``data:`` URIs through an application
  resolver, ``data:`` accepted for raster images only;
- CSS kept but filtered: no ``@import``, ``expression()``, bindings, escapes,
  and ``url()`` subject to the same rules as ``<img src>``;
- every surviving link rewritten to an opaque per-index URL, so the engine
  never navigates by itself: the widget maps the index back to the original
  target and reports it to the application.

html_to_lines() flattens sanitized HTML into styled text runs for backends
without an HTML engine (ncurses, GTK without WebKit); lines_to_pango() and
lines_to_simple_html() serialize those runs for the respective widgets.

This module deliberately imports nothing from manatools, so every backend can
use it without creating an import cycle.

License: LGPLv2+

@package manatools.aui
'''

import base64
import html as _html
import re
from html.parser import HTMLParser
from typing import Callable, List, NamedTuple, Optional
from urllib.parse import unquote, urljoin

__all__ = [
    "LINK_PREFIX",
    "SanitizedHtml",
    "sanitize_html",
    "link_index_from_url",
    "html_to_lines",
    "lines_to_pango",
    "lines_to_simple_html",
]

# Opaque link targets point at a reserved domain (RFC 2606 ``.invalid`` never
# resolves), so an engine that somehow followed one would go nowhere.
DOC_BASE_URL = "https://mana-htmlview.invalid/"
LINK_PREFIX = DOC_BASE_URL + "link/"

# Hard limits against hostile input ("giant tables", nesting bombs, huge
# inline images).  Content past MAX_INPUT_CHARS is dropped.
MAX_INPUT_CHARS = 8 * 1024 * 1024
MAX_DEPTH = 256
MAX_LINKS = 10000
MAX_STYLE_CHARS = 512 * 1024
MAX_ATTR_CHARS = 2048
MAX_INLINE_IMAGE_BYTES = 8 * 1024 * 1024
MAX_INLINE_TOTAL_BYTES = 32 * 1024 * 1024

# Removed together with everything they contain.
_DROP_WITH_CONTENT = frozenset({
    "script", "noscript", "template", "iframe", "frameset", "noframes",
    "object", "applet", "svg", "math", "canvas", "audio", "video", "select",
    "datalist", "title", "xml", "portal",
})

# Void elements that are dropped outright.
_DROP_VOID = frozenset({
    "input", "meta", "link", "source", "track", "param", "area", "keygen",
    "command", "basefont", "bgsound", "isindex", "frame", "embed",
})

# Void elements that survive.
_KEEP_VOID = frozenset({"br", "hr", "img", "wbr", "col"})

_ALLOWED_TAGS = frozenset({
    "a", "abbr", "address", "article", "aside", "b", "bdi", "bdo", "big",
    "blockquote", "br", "caption", "center", "cite", "code", "col",
    "colgroup", "dd", "del", "details", "dfn", "div", "dl", "dt", "em",
    "figcaption", "figure", "font", "footer", "h1", "h2", "h3", "h4", "h5",
    "h6", "header", "hr", "i", "img", "ins", "kbd", "li", "main", "mark",
    "nav", "ol", "p", "picture", "pre", "q", "rp", "rt", "ruby", "s", "samp",
    "section", "small", "span", "strike", "strong", "sub", "summary", "sup",
    "table", "tbody", "td", "tfoot", "th", "thead", "time", "tr", "tt", "u",
    "ul", "var", "wbr",
})

_GLOBAL_ATTRS = frozenset({
    "align", "valign", "bgcolor", "border", "cellpadding", "cellspacing",
    "color", "colspan", "rowspan", "dir", "face", "height", "width", "lang",
    "size", "style", "title", "class", "id", "span", "start", "type",
    "summary", "headers", "scope", "nowrap", "hspace", "vspace", "datetime",
    "reversed", "open", "abbr", "char", "charoff", "clear", "compact",
    "noshade",
})

_TAG_ATTRS = {
    "a": frozenset({"href", "name"}),
    "img": frozenset({"src", "alt"}),
    "table": frozenset({"background", "frame", "rules"}),
    "td": frozenset({"background"}),
    "th": frozenset({"background"}),
    "tr": frozenset({"background"}),
}

# <body> becomes a <div>: its presentational attributes are turned into CSS.
_BODY_STYLE_ATTRS = {"bgcolor": "background-color", "text": "color"}
_COLOR_VALUE_RE = re.compile(r"^#?[0-9a-zA-Z]{1,32}$")

_LINK_SCHEMES = frozenset({"http", "https", "mailto", "ftp", "tel", "news"})

_IMAGE_MIMES = frozenset({
    "image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp",
    "image/bmp",
})

# Browsers ignore ASCII tab/newline anywhere in a URL and C0/space at the
# start, so "java\nscript:" must be classified as "javascript:".
_URL_JUNK_RE = re.compile(r"[\x00-\x20\x7f]+")
_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")
_DATA_IMAGE_RE = re.compile(
    r"^data:image/(png|jpe?g|gif|webp|bmp);base64,[A-Za-z0-9+/]+=*$",
    re.IGNORECASE)
_CSS_PROP_RE = re.compile(r"^-?[a-z][a-z0-9\-]*$")
# Legacy properties that attach code to elements (IE behaviors, XBL).
_CSS_FORBIDDEN_PROPS = frozenset({"behavior", "-moz-binding", "binding"})
_CSS_FORBIDDEN_RE = re.compile(
    r"expression\s*\(|javascript\s*:|vbscript\s*:|-moz-binding|behavior\s*:"
    r"|@import|image-set\s*\(|(?<![a-z\-])image\s*\(|\bsrc\s*\(|\\|<",
    re.IGNORECASE)
_CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE | re.DOTALL)
_CSS_COMMENT_RE = re.compile(r"/\*.*?(\*/|$)", re.DOTALL)
_LINK_INDEX_RE = re.compile(r"/link/(\d+)$")


class SanitizedHtml(NamedTuple):
    """Result of sanitize_html().

    document:       complete HTML document (with a restrictive CSP meta tag)
    body:           sanitized body fragment, for engines fed with fragments
    links:          original link targets; index N is what LINK_PREFIX + N
                    (or the backend's own link_href(N)) stands for
    remote_blocked: number of remote resources that were not loaded
    """
    document: str
    body: str
    links: List[str]
    remote_blocked: int


def link_index_from_url(url) -> Optional[int]:
    """Return the link index encoded in an opaque link URL, or None."""
    try:
        m = _LINK_INDEX_RE.search(str(url or "").split("?", 1)[0].split("#", 1)[0])
        return int(m.group(1)) if m else None
    except Exception:
        return None


def _default_link_href(index: int) -> str:
    return f"{LINK_PREFIX}{index}"


def _compact_url(url: str):
    """Return (scheme or None, url with ignorable characters removed)."""
    compact = _URL_JUNK_RE.sub("", url or "")
    m = _SCHEME_RE.match(compact)
    return (m.group(1).lower() if m else None), compact


def _split_css(text: str, sep: str) -> List[str]:
    """Split CSS *text* on *sep* outside parentheses and quotes."""
    parts, buf, depth, quote = [], [], 0, None
    for ch in text:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == sep and depth == 0:
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    parts.append("".join(buf))
    return parts


def _find_block_end(text: str, start: int) -> int:
    """Index of the '}' closing the block opened just before *start*, or -1."""
    depth, quote = 1, None
    for i in range(start, len(text)):
        ch = text[i]
        if quote:
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


class _Sanitizer(HTMLParser):
    """Allow-list HTML rewriter; see sanitize_html()."""

    def __init__(self, allow_remote: bool, cid_resolver, link_href, resolve_base: bool):
        super().__init__(convert_charrefs=True)
        self.allow_remote = bool(allow_remote)
        self.cid_resolver = cid_resolver
        self.link_href = link_href
        self.resolve_base = bool(resolve_base)
        self.base_href = None
        self.out: List[str] = []
        self.stack: List[tuple] = []        # (source tag, emitted tag)
        self.links: List[str] = []
        self.remote_blocked = 0
        self.skip_tag = None
        self.skip_nest = 0
        self.in_style = False
        self.style_buf: List[str] = []
        self.style_len = 0
        self._cid_cache = {}
        self._inline_total = 0

    # -- URLs ---------------------------------------------------------------

    def _resolve_relative(self, url: str) -> Optional[str]:
        if not (self.resolve_base and self.base_href):
            return None
        try:
            joined = urljoin(self.base_href, url)
        except Exception:
            return None
        scheme, compact = _compact_url(joined)
        return compact if scheme in ("http", "https") else None

    def _link_target(self, url: str) -> Optional[str]:
        """Original target reported to the application, or None if refused."""
        if url is None:
            return None
        scheme, compact = _compact_url(url)
        if not compact:
            return None
        if scheme is None:
            return self._resolve_relative(compact) or compact
        return compact if scheme in _LINK_SCHEMES else None

    def _inline_cid(self, cid_url: str) -> Optional[str]:
        cid = unquote(cid_url[4:]).strip().strip("<>")
        if not cid or self.cid_resolver is None:
            return None
        if cid in self._cid_cache:
            return self._cid_cache[cid]
        result = None
        try:
            resolved = self.cid_resolver(cid)
            if resolved:
                data, mime = resolved
                mime = str(mime or "").split(";", 1)[0].strip().lower()
                if (isinstance(data, (bytes, bytearray)) and mime in _IMAGE_MIMES
                        and 0 < len(data) <= MAX_INLINE_IMAGE_BYTES
                        and self._inline_total + len(data) <= MAX_INLINE_TOTAL_BYTES):
                    self._inline_total += len(data)
                    result = f"data:{mime};base64,{base64.b64encode(bytes(data)).decode('ascii')}"
        except Exception:
            result = None
        self._cid_cache[cid] = result
        return result

    def _resource_url(self, url: str) -> Optional[str]:
        """URL an engine may load for an image/background, or None."""
        scheme, compact = _compact_url(url)
        if not compact:
            return None
        if scheme == "data":
            if len(compact) <= MAX_INLINE_IMAGE_BYTES * 2 and _DATA_IMAGE_RE.match(compact):
                return compact
            return None
        if scheme == "cid":
            return self._inline_cid(compact)
        if scheme in ("http", "https"):
            if self.allow_remote:
                return compact
            self.remote_blocked += 1
            return None
        if scheme is None:
            resolved = self._resolve_relative(compact)
            if resolved:
                if self.allow_remote:
                    return resolved
                self.remote_blocked += 1
        return None

    # -- CSS ----------------------------------------------------------------

    def _css_value(self, value: str) -> Optional[str]:
        """Filter one declaration value; None drops the declaration."""
        if _CSS_FORBIDDEN_RE.search(value):
            return None

        def _sub(m):
            safe = self._resource_url(m.group(2))
            if safe is None or re.search(r"[\"'()\s<>]", safe):
                return "none"
            return f'url("{safe}")'

        value = _CSS_URL_RE.sub(_sub, value)
        # A url( left over once the vetted ones are removed is malformed or
        # obfuscated: drop the whole declaration.
        if re.search(r"url\s*\(", re.sub(r'url\("[^"]*"\)', "", value), re.IGNORECASE):
            return None
        return value

    def _css_declarations(self, text: str) -> str:
        decls = []
        for decl in _split_css(text, ";"):
            if ":" not in decl:
                continue
            prop, value = decl.split(":", 1)
            prop = prop.strip().lower()
            value = value.strip()
            if not value or not _CSS_PROP_RE.match(prop) or prop in _CSS_FORBIDDEN_PROPS:
                continue
            value = self._css_value(value)
            if value is not None:
                decls.append(f"{prop}: {value}")
        return "; ".join(decls)

    def _stylesheet(self, css: str, depth: int = 0) -> str:
        css = _CSS_COMMENT_RE.sub("", css)
        out, pos = [], 0
        while pos < len(css):
            brace = css.find("{", pos)
            semi = css.find(";", pos)
            if brace == -1:
                break
            if semi != -1 and semi < brace:
                # Statement at-rule (@import, @charset, @namespace): dropped.
                pos = semi + 1
                continue
            prelude = css[pos:brace].strip()
            end = _find_block_end(css, brace + 1)
            if end == -1:
                break
            inner = css[brace + 1:end]
            pos = end + 1
            if not prelude or len(prelude) > 2000 or re.search(r"[<\\]", prelude):
                continue
            if prelude.startswith("@"):
                name = prelude[1:].split(None, 1)[0].lower() if len(prelude) > 1 else ""
                if name in ("media", "supports") and depth < 4:
                    nested = self._stylesheet(inner, depth + 1)
                    if nested:
                        out.append(f"{prelude} {{ {nested} }}")
                # @font-face, @keyframes, @page, ... are dropped.
                continue
            decls = self._css_declarations(inner)
            if decls:
                out.append(f"{prelude} {{ {decls} }}")
        return "\n".join(out)

    # -- attributes ---------------------------------------------------------

    @staticmethod
    def _body_attrs(attrs) -> list:
        """Fold <body> presentational attributes into a style declaration."""
        styles, kept = [], []
        for name, value in attrs:
            name = (name or "").lower()
            value = (value or "").strip()
            if name in _BODY_STYLE_ATTRS and _COLOR_VALUE_RE.match(value):
                styles.append(f"{_BODY_STYLE_ATTRS[name]}: {value}")
            elif name == "background" and value:
                styles.append(f"background-image: url({value})")
            elif name == "style":
                styles.append(value)
            elif name != "class":
                kept.append((name, value))
        if styles:
            kept.append(("style", "; ".join(styles)))
        return kept

    def _attrs(self, tag: str, attrs) -> List[str]:
        allowed = _TAG_ATTRS.get(tag, frozenset())
        out, seen, has_title, link_title = [], set(), False, None
        for name, value in attrs:
            name = (name or "").lower()
            if not name or name in seen or name.startswith("on"):
                continue
            if name not in _GLOBAL_ATTRS and name not in allowed:
                continue
            seen.add(name)
            value = "" if value is None else str(value)[:MAX_ATTR_CHARS]
            if name == "href":
                target = self._link_target(value)
                if target is None or len(self.links) >= MAX_LINKS:
                    continue
                index = len(self.links)
                self.links.append(target)
                value = self.link_href(index)
                link_title = target
            elif name in ("src", "background"):
                value = self._resource_url(value)
                if value is None:
                    continue
            elif name == "style":
                value = self._css_declarations(value)
                if not value:
                    continue
            elif name == "title":
                has_title = True
            out.append(f'{name}="{_html.escape(value, quote=True)}"')
        # Show the real destination on hover: mail links lie about it often.
        if link_title is not None and not has_title:
            out.append(f'title="{_html.escape(link_title, quote=True)}"')
        return out

    # -- parser callbacks ---------------------------------------------------

    def handle_starttag(self, tag, attrs):
        if self.skip_tag is not None:
            if tag == self.skip_tag:
                self.skip_nest += 1
            return
        if self.in_style:
            return
        if tag in _DROP_WITH_CONTENT:
            self.skip_tag, self.skip_nest = tag, 1
            return
        if tag == "base":
            if self.base_href is None:
                href = dict(attrs).get("href")
                scheme, compact = _compact_url(href or "")
                if scheme in ("http", "https"):
                    self.base_href = compact
            return
        if tag == "style":
            self.in_style = True
            self.style_buf, self.style_len = [], 0
            return
        if tag in _DROP_VOID or tag in ("html", "head"):
            return
        emitted = "div" if tag == "body" else tag
        if (emitted not in _ALLOWED_TAGS and tag != "body") or len(self.stack) >= MAX_DEPTH:
            return  # unwrap: keep the content, drop the element
        if tag == "body":
            parts = self._attrs("div", self._body_attrs(attrs)) + ['class="mana-html-body"']
        else:
            parts = self._attrs(tag, attrs)
        self.out.append(f"<{emitted}{' ' + ' '.join(parts) if parts else ''}>")
        if emitted not in _KEEP_VOID:
            self.stack.append((tag, emitted))

    def handle_endtag(self, tag):
        if self.skip_tag is not None:
            if tag == self.skip_tag:
                self.skip_nest -= 1
                if self.skip_nest <= 0:
                    self.skip_tag = None
            return
        if tag == "style" and self.in_style:
            self.in_style = False
            css = self._stylesheet("".join(self.style_buf))
            if css:
                self.out.append(f"<style>{css}</style>")
            return
        if self.in_style or tag in _KEEP_VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                while len(self.stack) > i:
                    self.out.append(f"</{self.stack.pop()[1]}>")
                return

    def handle_data(self, data):
        if self.skip_tag is not None:
            return
        if self.in_style:
            if self.style_len < MAX_STYLE_CHARS:
                self.style_buf.append(data)
                self.style_len += len(data)
            return
        self.out.append(_html.escape(data, quote=False))

    # Comments, doctype, processing instructions, CDATA: all dropped.
    def handle_comment(self, data):
        pass

    def handle_decl(self, decl):
        pass

    def handle_pi(self, data):
        pass

    def unknown_decl(self, data):
        pass

    def finish(self) -> str:
        self.close()
        while self.stack:
            self.out.append(f"</{self.stack.pop()[1]}>")
        return "".join(self.out)


def _document(body: str, allow_remote: bool) -> str:
    img_src = "data: http: https:" if allow_remote else "data:"
    csp = (f"default-src 'none'; img-src {img_src}; style-src 'unsafe-inline'; "
           "font-src data:; base-uri 'none'; form-action 'none'")
    return ('<!DOCTYPE html><html><head><meta charset="utf-8">'
            f'<meta http-equiv="Content-Security-Policy" content="{csp}">'
            '<meta name="referrer" content="no-referrer">'
            '<style>html{color-scheme:light}'
            'body{margin:8px;overflow-wrap:anywhere}'
            'img{max-width:100%;height:auto}</style>'
            f'</head><body>{body}</body></html>')


def sanitize_html(source: str, *, allow_remote: bool = False,
                  cid_resolver: Optional[Callable] = None,
                  link_href: Optional[Callable[[int], str]] = None,
                  resolve_base: bool = False) -> SanitizedHtml:
    """Sanitize untrusted HTML for display.

    Args:
        source:       untrusted HTML.
        allow_remote: when False, http(s) images/backgrounds/CSS urls are
                      removed and counted in ``remote_blocked``.
        cid_resolver: callable(content_id) -> (bytes, mime) or None, used to
                      inline ``cid:`` images.  Only raster image types load.
        link_href:    callable(index) -> href written into the output for the
                      index-th link (default: LINK_PREFIX + index).
        resolve_base: resolve relative links against the document's own
                      ``<base href>`` (http/https only) instead of reporting
                      them verbatim.

    Returns:
        SanitizedHtml.  Never raises on malformed input.
    """
    text = str(source or "")[:MAX_INPUT_CHARS]
    parser = _Sanitizer(allow_remote, cid_resolver, link_href or _default_link_href, resolve_base)
    try:
        parser.feed(text)
        body = parser.finish()
    except Exception:
        # HTMLParser is lenient, but never let a parser bug leak raw input.
        body = _html.escape(text, quote=False)
        parser.links, parser.remote_blocked = [], 0
    return SanitizedHtml(_document(body, allow_remote), body, parser.links, parser.remote_blocked)


# ---------------------------------------------------------------------------
# Text rendering for engine-less backends
# ---------------------------------------------------------------------------

_BLOCK_TAGS = frozenset({
    "address", "article", "aside", "center", "dd", "details", "div", "dl",
    "dt", "figcaption", "figure", "footer", "header", "main", "nav",
    "section", "summary", "caption",
})
_PARAGRAPH_TAGS = frozenset({
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "table", "pre",
})
_BOLD_TAGS = frozenset({"b", "strong", "h1", "h2", "h3", "h4", "h5", "h6", "th"})
_ITALIC_TAGS = frozenset({"i", "em", "cite", "var", "dfn"})
_UNDERLINE_TAGS = frozenset({"u", "ins"})
_HR_WIDTH = 40


class _TextRenderer(HTMLParser):
    """Flattens sanitized HTML into lines of styled runs."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines: List[list] = [[]]
        self.bold = self.italic = self.underline = 0
        self.link = None
        self.pre = 0
        self.quote = 0
        self.in_style = False
        self.lists: List[list] = []     # [ordered, counter]
        self.cells_in_row = 0

    # -- line helpers -------------------------------------------------------

    def _line_empty(self) -> bool:
        return not any(seg["text"].strip() for seg in self.lines[-1])

    def _newline(self):
        self.lines.append([])

    def _break(self, blank: bool = False):
        if not self._line_empty():
            self._newline()
        if blank and len(self.lines) > 1:
            prev = self.lines[-2]
            if any(seg["text"].strip() for seg in prev):
                self._newline()

    def _emit(self, text: str, **style):
        if not text:
            return
        line = self.lines[-1]
        if not line and self.quote:
            line.append(self._seg("> " * self.quote))
        seg = self._seg(text, **style)
        if line and all(line[-1][k] == seg[k] for k in ("bold", "italic", "underline", "link")):
            line[-1]["text"] += text
        else:
            line.append(seg)

    def _seg(self, text, **style):
        return {
            "text": text,
            "bold": style.get("bold", self.bold > 0),
            "italic": style.get("italic", self.italic > 0),
            "underline": style.get("underline", self.underline > 0 or self.link is not None),
            "link": style.get("link", self.link),
        }

    # -- parser callbacks ---------------------------------------------------

    def handle_starttag(self, tag, attrs):
        if self.in_style:
            return
        at = dict(attrs)
        if tag == "style":
            self.in_style = True
        elif tag == "br":
            self._newline()
        elif tag == "hr":
            self._break()
            self._emit("─" * _HR_WIDTH, bold=False, italic=False, underline=False, link=None)
            self._newline()
        elif tag == "img":
            alt = (at.get("alt") or "").strip()
            if alt:
                self._emit(f"[{alt}]")
        elif tag == "a":
            self.link = link_index_from_url(at.get("href"))
        elif tag in ("ul", "ol"):
            self._break(blank=not self.lists)
            self.lists.append([tag == "ol", 0])
        elif tag == "li":
            self._break()
            indent = "  " * max(0, len(self.lists) - 1)
            if self.lists and self.lists[-1][0]:
                self.lists[-1][1] += 1
                marker = f"{self.lists[-1][1]}. "
            else:
                marker = "• "
            self._emit(indent + marker, bold=False, italic=False, underline=False, link=None)
        elif tag == "tr":
            self._break()
            self.cells_in_row = 0
        elif tag in ("td", "th"):
            if self.cells_in_row:
                self._emit(" | ", bold=False, italic=False, underline=False, link=None)
            self.cells_in_row += 1
        elif tag == "blockquote":
            self._break()
            self.quote += 1
        elif tag in _PARAGRAPH_TAGS:
            self._break(blank=True)
        elif tag in _BLOCK_TAGS:
            self._break()
        if tag == "pre":
            self.pre += 1
        if tag in _BOLD_TAGS:
            self.bold += 1
        if tag in _ITALIC_TAGS:
            self.italic += 1
        if tag in _UNDERLINE_TAGS:
            self.underline += 1

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False
            return
        if self.in_style:
            return
        if tag == "a":
            self.link = None
        elif tag in ("ul", "ol"):
            if self.lists:
                self.lists.pop()
            self._break(blank=not self.lists)
        elif tag == "li":
            self._break()
        elif tag == "blockquote":
            self._break()
            self.quote = max(0, self.quote - 1)
        elif tag in _PARAGRAPH_TAGS:
            self._break(blank=True)
        elif tag in _BLOCK_TAGS or tag == "tr":
            self._break()
        if tag == "pre":
            self.pre = max(0, self.pre - 1)
        if tag in _BOLD_TAGS:
            self.bold = max(0, self.bold - 1)
        if tag in _ITALIC_TAGS:
            self.italic = max(0, self.italic - 1)
        if tag in _UNDERLINE_TAGS:
            self.underline = max(0, self.underline - 1)

    def handle_data(self, data):
        if self.in_style:
            return
        if self.pre:
            chunks = data.split("\n")
            for i, chunk in enumerate(chunks):
                if i:
                    self._newline()
                self._emit(chunk.replace("\t", "    "))
            return
        text = re.sub(r"\s+", " ", data)
        if self._line_empty():
            text = text.lstrip()
        elif text.startswith(" ") and self.lines[-1][-1]["text"].endswith(" "):
            text = text[1:]
        self._emit(text)

    def result(self) -> List[list]:
        self.close()
        lines = self.lines
        while len(lines) > 1 and not any(s["text"].strip() for s in lines[-1]):
            lines.pop()
        while len(lines) > 1 and not any(s["text"].strip() for s in lines[0]):
            lines.pop(0)
        return lines


def html_to_lines(body: str) -> List[list]:
    """Flatten sanitized HTML into lines of runs.

    Each line is a list of dicts with keys text, bold, italic, underline and
    link (the link index, or None).  Feed it sanitize_html().body: the input
    is trusted to be sanitized already.
    """
    renderer = _TextRenderer()
    try:
        renderer.feed(body or "")
        return renderer.result()
    except Exception:
        return [[{"text": re.sub(r"<[^>]*>", "", body or ""), "bold": False,
                  "italic": False, "underline": False, "link": None}]]


def _wrap_run(seg, text: str, open_link: Callable[[int], str], close_link: str) -> str:
    out = text
    if seg["underline"] and seg["link"] is None:
        out = f"<u>{out}</u>"
    if seg["italic"]:
        out = f"<i>{out}</i>"
    if seg["bold"]:
        out = f"<b>{out}</b>"
    if seg["link"] is not None:
        out = f"{open_link(seg['link'])}{out}{close_link}"
    return out


def _anchor_opener(href: Optional[Callable[[int], str]]) -> Callable[[int], str]:
    href = href or _default_link_href
    return lambda n: f'<a href="{_html.escape(href(n), quote=True)}">'


def lines_to_pango(lines: List[list], href: Optional[Callable[[int], str]] = None) -> str:
    """Serialize html_to_lines() output as Pango markup for a Gtk.Label.

    Links become ``<a href="href(N)">`` (default LINK_PREFIX + N).
    """
    opener = _anchor_opener(href)
    return "\n".join(
        "".join(_wrap_run(seg, _html.escape(seg["text"], quote=False), opener, "</a>")
                for seg in line)
        for line in lines)


def lines_to_simple_html(lines: List[list], href: Optional[Callable[[int], str]] = None) -> str:
    """Serialize html_to_lines() output as a tiny HTML subset (b/i/u/a/br),
    understood by the curses YRichText parser and by any HTML engine.
    Links become ``<a href="href(N)">`` (default LINK_PREFIX + N).
    """
    opener = _anchor_opener(href)
    return "<br>".join(
        "".join(_wrap_run(seg, _html.escape(seg["text"], quote=True), opener, "</a>")
                for seg in line)
        for line in lines)
