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