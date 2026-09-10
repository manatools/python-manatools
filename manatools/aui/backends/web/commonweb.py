"""
Common utilities shared across all web backend widgets.

Author: Matteo Pasotti <xquiet@coriolite.com>

License: LGPLv2+

"""

import html
import re
import threading
from typing import Optional

# ---------------------------------------------------------------------------
# Initial-render context flag
# ---------------------------------------------------------------------------

_render_context = threading.local()


def set_initial_render(flag: bool):
    """Mark the current thread as performing an initial HTTP page render.

    When True, widgets that support deferred loading (e.g. YTable) emit a
    lightweight skeleton placeholder instead of their full content.  The real
    content is pushed to the browser via WebSocket once the connection opens.
    """
    _render_context.initial = flag


def is_initial_render() -> bool:
    """Return True if the current thread is performing an initial HTTP page render."""
    return getattr(_render_context, 'initial', False)

def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return html.escape(str(text), quote=False) if text else ""


def format_label_with_shortcut(label: str) -> str:
    """
    Convert a raw (unescaped) label with '&X' shortcut notation to safe HTML.
    '&X'  -> '<u>X</u>'   (shortcut underline)
    '&&'  -> '&amp;'      (literal ampersand)
    All other text is HTML-escaped.

    IMPORTANT: pass the *raw* label here, NOT pre-escaped text.
    Escaping before calling this function will corrupt the output.
    """
    if not label:
        return ""
    parts = []
    i = 0
    while i < len(label):
        if label[i] == '&':
            if i + 1 < len(label):
                next_ch = label[i + 1]
                if next_ch == '&':
                    parts.append('&amp;')
                    i += 2
                else:
                    parts.append(f'<u>{html.escape(next_ch, quote=False)}</u>')
                    i += 2
            else:
                parts.append('&amp;')
                i += 1
        else:
            parts.append(html.escape(label[i], quote=False))
            i += 1
    return "".join(parts)


def extract_shortcut(label: str) -> Optional[str]:
    """Extract the shortcut character from a label with &X notation."""
    if not label:
        return None
    match = re.search(r'&([^&])', label)
    return match.group(1).lower() if match else None


def strip_shortcut(label: str) -> str:
    """Remove &X shortcut notation from label, keeping the character."""
    if not label:
        return ""
    result = re.sub(r'&&', '\x00', label)
    result = re.sub(r'&(.)', r'\1', result)
    return result.replace('\x00', '&')


def layout_children_html(children, dim) -> str:
    """Render *children* of a box, applying their layout weights as flex rules.

    Mirrors the Qt backend's stretch-factor semantics (see ``hboxqt.py``):
    if any child carries a positive weight in *dim*, those weights are used as
    the proportions; otherwise stretchable children share the free space
    equally and the rest keep their natural size.

    A weight of *n* becomes ``flex: n 1 0`` so the ratio between siblings holds
    regardless of content width — that is what ``setWeight(YD_HORIZ, 84)`` vs
    ``16`` is asking for.  When no weight is set anywhere, only growing
    children get an inline rule, so widgets that rely on the stylesheet's
    defaults keep behaving exactly as before.

    Args:
        children: Child widgets, in layout order.
        dim:      The box's main dimension (YUIDimension.YD_HORIZ / YD_VERT).

    Returns:
        str: Concatenated HTML of all children.
    """
    from ...yui_common import YUIDimension

    horizontal = dim in (YUIDimension.YD_HORIZ, YUIDimension.Horizontal)
    cross_dim = YUIDimension.YD_VERT if horizontal else YUIDimension.YD_HORIZ

    def _weight(child):
        try:
            return max(0, int(child.weight(dim) or 0))
        except Exception:
            return 0

    def _stretchable(child, dimension):
        try:
            return bool(child.stretchable(dimension))
        except Exception:
            return False

    weights = [_weight(child) for child in children]
    has_positive = any(w > 0 for w in weights)

    parts = []
    for child, weight in zip(children, weights):
        html = child.render()
        grow = weight if has_positive else (1 if _stretchable(child, dim) else 0)

        styles = []
        if grow > 0:
            styles.append(f"flex: {grow} 1 0")
            # Let the child shrink below its content size, but never override a
            # minimum the widget set for itself (e.g. YMinSize/YMinWidth).
            min_prop = "min-width" if horizontal else "min-height"
            if not declares_style(html, min_prop):
                styles.append(f"{min_prop}: 0")
        elif has_positive:
            # An explicit weight of 0 among weighted siblings means "natural
            # size"; say so inline, or the stylesheet default would still grow.
            styles.append("flex: 0 0 auto")

        if _stretchable(child, cross_dim):
            styles.append("align-self: stretch")

        if styles:
            html = merge_inline_style(html, "; ".join(styles))
        parts.append(html)

    return "".join(parts)


_OPEN_TAG_RE = re.compile(r'<\s*[A-Za-z][^>]*?>')
_STYLE_ATTR_RE = re.compile(r'style\s*=\s*"([^"]*)"')


def declares_style(html: str, prop: str) -> bool:
    """Return True if the outermost element of *html* already sets *prop*."""
    if not html:
        return False
    match = _OPEN_TAG_RE.search(html)
    if not match:
        return False
    style_match = _STYLE_ATTR_RE.search(match.group(0))
    if not style_match:
        return False
    declarations = (d.split(':', 1)[0].strip().lower()
                    for d in style_match.group(1).split(';') if ':' in d)
    return prop.lower() in declarations


def merge_inline_style(html: str, style: str) -> str:
    """Append *style* declarations to the outermost element of *html*.

    Declarations are appended rather than prepended so they win over whatever
    the widget emitted itself; an element with no ``style`` attribute gets one.
    Returns *html* unchanged when it has no element to attach to.
    """
    if not html or not style:
        return html

    match = _OPEN_TAG_RE.search(html)
    if not match:
        return html

    tag = match.group(0)
    style_match = _STYLE_ATTR_RE.search(tag)
    if style_match:
        existing = style_match.group(1).rstrip().rstrip(';')
        merged = f"{existing}; {style}" if existing else style
        new_tag = tag[:style_match.start()] + f'style="{merged}"' + tag[style_match.end():]
    else:
        new_tag = tag[:-1].rstrip() + f' style="{style}">'

    return html[:match.start()] + new_tag + html[match.end():]


def build_css_classes(*classes: str) -> str:
    """Build a CSS class string from multiple class names, filtering empty."""
    return " ".join(c for c in classes if c)


def build_style(**styles) -> str:
    """Build an inline style string from keyword arguments."""
    parts = []
    for key, value in styles.items():
        if value is not None:
            # Convert Python names to CSS (background_color -> background-color)
            css_key = key.replace('_', '-')
            parts.append(f"{css_key}: {value}")
    return "; ".join(parts) if parts else ""


def widget_attrs(widget_id: str, widget_class: str, enabled: bool = True, 
                 visible: bool = True, extra_classes: str = "",
                 extra_attrs: dict = None) -> str:
    """
    Build common HTML attributes for a widget element.
    
    Returns a string like: id="..." class="..." data-widget-class="..." [disabled] [hidden]
    """
    classes = build_css_classes(f"mana-{widget_class.lower()}", extra_classes)
    
    attrs = [
        f'id="{escape_html(widget_id)}"',
        f'class="{classes}"',
        f'data-widget-class="{escape_html(widget_class)}"',
    ]
    
    if not enabled:
        attrs.append('disabled')
    
    if not visible:
        attrs.append('style="display: none"')
    
    if extra_attrs:
        for key, value in extra_attrs.items():
            if value is True:
                attrs.append(key)
            elif value is not None and value is not False:
                attrs.append(f'{key}="{escape_html(str(value))}"')
    
    return " ".join(attrs)