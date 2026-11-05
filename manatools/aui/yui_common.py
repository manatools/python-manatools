"""
Common base classes and definitions shared across all backends
"""

from enum import Enum
import fnmatch
import math
import os
import re
import shutil
import subprocess
import uuid
from typing import Optional

from . import yui_html as _yui_html

# ---------------------------------------------------------------------------
# Filesystem helpers for the backends' file/directory choosers
# ---------------------------------------------------------------------------

def parse_filter_patterns(filter_str: str):
    """Split a libyui-style filter string into a list of glob patterns.

    ``"*.txt;*.md"`` becomes ``["*.txt", "*.md"]``.  An empty or unparseable
    filter yields an empty list, which callers treat as "accept every file".
    """
    try:
        if not filter_str:
            return []
        return [p.strip() for p in filter_str.split(';') if p.strip()]
    except Exception:
        return []


def documents_dir() -> str:
    """Return the user's XDG documents directory, falling back to home.

    The name is locale-dependent (Documents, Documenti, Dokumente, …), so it
    must be resolved at runtime rather than hardcoded.  ``xdg-user-dir`` is
    tried first; if the binary is missing, ~/.config/user-dirs.dirs is parsed
    directly.  Home is returned whenever the lookup fails or names a directory
    that does not exist.
    """
    try:
        xdg = shutil.which("xdg-user-dir")
        if xdg:
            out = subprocess.run(
                [xdg, "DOCUMENTS"],
                capture_output=True, text=True, timeout=2,
            ).stdout.strip()
            if out and os.path.isdir(out):
                return out
    except Exception:
        pass

    # No xdg-user-dir binary (minimal installs): read the config it would.
    try:
        config = os.path.join(
            os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
            "user-dirs.dirs")
        with open(config, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line.startswith("XDG_DOCUMENTS_DIR"):
                    continue
                _, _, value = line.partition("=")
                path = value.strip().strip('"').replace(
                    "$HOME", os.path.expanduser("~"))
                if path and os.path.isdir(path):
                    return path
    except Exception:
        pass

    return os.path.expanduser("~")


def list_entries(current_dir: str, select_file: bool, patterns):
    """List *current_dir* for a file chooser.

    Returns ``(label, path, type)`` triples where *type* is ``'dir'`` or
    ``'file'``: the parent entry ``".."`` first (unless already at the root),
    then directories (labelled with a trailing ``/``), then files, each group
    sorted case-insensitively.  Files are omitted entirely when *select_file*
    is False, and otherwise kept only if they match one of *patterns*.

    Symlinks are resolved, so a symlinked directory such as /media/… is listed
    as a directory rather than silently dropped.  Unreadable entries and an
    unreadable directory are skipped rather than raising, so a chooser never
    dies on a permission error.
    """
    entries = []
    try:
        parent = os.path.dirname(current_dir.rstrip(os.sep)) or current_dir
        if parent and parent != current_dir:
            entries.append(("..", parent, 'dir'))

        with os.scandir(current_dir) as it:
            dirs = []
            files = []
            for e in it:
                try:
                    if e.is_dir():
                        dirs.append((e.name + '/', e.path, 'dir'))
                    elif e.is_file():
                        if not select_file:
                            continue
                        if not patterns or any(
                                fnmatch.fnmatch(e.name, pat) for pat in patterns):
                            files.append((e.name, e.path, 'file'))
                except OSError:
                    # Broken symlink or unreadable entry: skip it.
                    continue

        dirs.sort(key=lambda x: x[0].lower())
        files.sort(key=lambda x: x[0].lower())
        entries.extend(dirs)
        entries.extend(files)
    except OSError:
        # Unreadable directory: offer the parent entry alone so the user can
        # navigate back out.
        pass
    return entries


# Enums
# Backwards-compatible aliases: allow using `YUIDimension.Horizontal` / `Vertical`
# in code that expects more readable names.
class YUIDimension(Enum):
    YD_HORIZ = 0
    Horizontal = 0
    YD_VERT = 1
    Vertical = 1

class YAlignmentType(Enum):
    YAlignUnchanged = 0
    YAlignBegin = 1
    YAlignEnd = 2
    YAlignCenter = 3

class YDialogType(Enum):
    YMainDialog = 0
    YPopupDialog = 1
    YWizardDialog = 2

class YDialogColorMode(Enum):
    YDialogNormalColor = 0
    YDialogInfoColor = 1
    YDialogWarnColor = 2

class YEventType(Enum):
    NoEvent = 0
    WidgetEvent = 1
    MenuEvent = 2
    KeyEvent = 3
    CancelEvent = 4
    TimeoutEvent = 5

class YEventReason(Enum):
    Activated = 0
    ValueChanged = 1
    SelectionChanged = 2

class YCheckBoxState(Enum):
    YCheckBox_dont_care = -1
    YCheckBox_off = 0
    YCheckBox_on = 1

class YButtonRole(Enum):
    YCustomButton = 0
    YOKButton = 1
    YCancelButton = 2
    YHelpButton = 3

class YLogViewFocus(Enum):
    """Scroll-focus policy for YLogView widgets.

    HEAD
        The viewport is anchored to the first (oldest) line.  New lines
        appended at the bottom do **not** move the viewport.  This is the
        default behaviour used e.g. for debug consoles where the user
        wants to read from the beginning.

    TAIL
        The viewport follows the last (newest) line.  Every call to
        :meth:`appendLines` scrolls the view to the bottom so the freshly
        added content is always visible.  Typical use-case: live
        transaction/download progress logs.
    """
    HEAD = 0   # anchor at first line (default)
    TAIL = 1   # follow last line on every append

class YHtmlBasePolicy(Enum):
    """How YHtmlView treats relative URLs and the document's own ``<base>``.

    NoBase
        ``<base href>`` is ignored.  Relative links are reported to the
        application verbatim; relative resources never load.  Default.

    DocumentBase
        Relative links are resolved against the document's ``<base href>``
        (http/https only) before being reported.  Relative images resolve
        too, and then follow the remote-content rule (setAllowRemote).
    """
    NoBase = 0
    DocumentBase = 1

class YChartLegendPosition(Enum):
    """Where YChartPie places its legend relative to the pie."""
    Right = 0
    Bottom = 1
    Hidden = 2

class YChartBarOrientation(Enum):
    """Direction YChartBar bars grow in."""
    Vertical = 0      # bars grow up, categories along the x axis
    Horizontal = 1    # bars grow right, categories along the y axis

# Exceptions
class YUIException(Exception):
    pass

class YUIWidgetNotFoundException(YUIException):
    pass

class YUINoDialogException(YUIException):
    pass

class YUIInvalidWidgetException(YUIException):
    pass

# Events
class YEvent:
    def __init__(self, event_type=YEventType.NoEvent, widget=None, reason=None):
        self._event_type = event_type
        self._widget = widget
        self._reason = reason
        self._serial = 0
    
    def eventType(self):
        return self._event_type
    
    def widget(self):
        return self._widget
    
    def reason(self):
        return self._reason
    
    def serial(self):
        return self._serial

class YWidgetEvent(YEvent):
    """Event generated by widgets"""
    def __init__(self, widget=None, reason=YEventReason.Activated, event_type=YEventType.WidgetEvent):
        super().__init__(event_type, widget, reason)

class YKeyEvent(YEvent):
    def __init__(self, key_symbol, focus_widget=None):
        super().__init__(YEventType.KeyEvent, focus_widget)
        self._key_symbol = key_symbol
    
    def keySymbol(self):
        return self._key_symbol
    
    def focusWidget(self):
        return self.widget()

class YMenuEvent(YEvent):
    def __init__(self, item=None, id=None):
        super().__init__(YEventType.MenuEvent)
        self._item = item
        self._id = id
    
    def item(self):
        return self._item
    
    def id(self):
        return self._id

class YTimeoutEvent(YEvent):
    """Event generated on timeout"""
    def __init__(self):
        super().__init__(YEventType.TimeoutEvent)

class YCancelEvent(YEvent):
    def __init__(self):
        super().__init__(YEventType.CancelEvent)

# Base Widget Class
class YWidget:
    _widget_counter = 0
    
    def __init__(self, parent=None):
        YWidget._widget_counter += 1
        self._id = f"widget_{YWidget._widget_counter}"
        self._parent = parent
        self._children = []
        self._enabled = True
        self._visible = True
        self._help_text = ""
        self._backend_widget = None
        self._stretchable_horiz = False
        self._stretchable_vert = False
        self._weight_horiz = 0
        self._weight_vert = 0
        # NOTE: Notify property should be False for back compatibility, 
        # but backends has been implemented as True
        self._notify = True
        self._auto_shortcut = False
        self._function_key = 0
        
        if parent and hasattr(parent, 'addChild'):
            parent.addChild(self)
    
    def widgetClass(self):
        return self.__class__.__name__
    
    def widgetPathName(self):
        ''' Return the full path name of this widget in the hierarchy. '''
        return f"{self._parent.widgetPathName()}/{self.widgetClass()}({self._id})" if self._parent else f"/{self.widgetClass()}({self._id})"
    
    def id(self):
        ''' Return the unique identifier of this widget. '''
        return self._id

    def debugLabel(self):
        return f"{self.widgetClass()}({self._id})"
    
    def helpText(self):
        ''' Return the help text (tooltip) for this widget. '''
        return self._help_text
    
    def setHelpText(self, help_text):
        ''' Set the help text (tooltip) for this widget. '''
        self._help_text = help_text
    
    def hasChildren(self):
        return len(self._children) > 0
    
    def firstChild(self):
        return self._children[0] if self._children else None
    
    def lastChild(self):
        return self._children[-1] if self._children else None
    
    def childrenBegin(self):
        return iter(self._children)
    
    def childrenEnd(self):
        return iter([])
    
    def childrenCount(self):
        return len(self._children)
    
    def addChild(self, child):
        if child not in self._children:
            self._children.append(child)
            child._parent = self
            if self.isEnabled() is False:
                child._enabled = False
    
    def removeChild(self, child):
        if child in self._children:
            self._children.remove(child)
            child._parent = None

    def deleteChildren(self):
        """
        Remove all logical children from this widget.

        This clears the internal children list and detaches each child's
        parent reference. Backend containers that render children should
        override this method to also clear any backend layout or content
        area. For generic widgets, this only affects the logical model.
        """
        try:
            for ch in list(self._children):
                try:
                    ch._parent = None
                except Exception:
                    pass
            self._children.clear()
        except Exception:
            # Best-effort: ignore failures and keep model consistent
            try:
                self._children = []
            except Exception:
                pass
    
    def parent(self):
        return self._parent
    
    def hasParent(self):
        return self._parent is not None
    
    def findDialog(self):
        """Find the parent dialog of this widget."""
        parent = getattr(self, '_parent', None)
        while parent is not None and parent.widgetClass() != 'YDialog':
            parent = getattr(parent, '_parent', None)
        return parent

    def setEnabled(self, enabled=True):
        '''
           Enable or disable the widget. i.e. make it accept or reject user input.
           Derived backend classes must implement _set_backend_enabled to apply 
           the change to the actual backend widget.
        '''
        self._enabled = enabled
        self._set_backend_enabled(enabled)
    
    def setDisabled(self):
        ''' Disenable the widget. '''
        self.setEnabled(False)
    
    def isEnabled(self):
        ''' Return whether the widget is enabled. '''
        return self._enabled

    def visible(self) -> bool:
        ''' Retunr the visibility of the widget. '''
        return bool(self._visible)
    
    def setVisible(self, visible:bool=True):
        ''' Set the visibility of the widget. Backend-specific implementation required. '''
        self._visible = bool(visible)
    
    def stretchable(self, dim):
        if dim == YUIDimension.YD_HORIZ:
            return self._stretchable_horiz
        else:
            return self._stretchable_vert
    
    def setStretchable(self, dim, new_stretch: bool):
        if dim == YUIDimension.YD_HORIZ:
            self._stretchable_horiz = new_stretch
        else:
            self._stretchable_vert = new_stretch
    
    def weight(self, dim):
        """Return the layout weight for the given dimension.

        The weight controls how extra space is distributed among stretchable
        widgets inside a container. A widget with a larger weight receives a
        proportionally larger share of the remaining space. The default weight
        is 0 (no preference). Any non-negative integer is a valid weight value;
        relative ratios (e.g. 67 vs 33 for a 2/3-1/3 split) are common.

        Args:
            dim: YUIDimension.YD_HORIZ or YUIDimension.YD_VERT.

        Returns:
            int: Current weight (>= 0) for the requested dimension.
        """
        if dim == YUIDimension.YD_HORIZ:
            return self._weight_horiz
        else:
            return self._weight_vert

    def setWeight(self, dim, weight: int):
        """Set the layout weight for the given dimension.

        Weights are non-negative integers used by container backends to
        distribute available space proportionally among children.  There is no
        upper limit; what matters is the ratio between sibling weights
        (e.g. setWeight(YD_VERT, 67) paired with setWeight(YD_VERT, 33) will
        give the first widget approximately twice the space of the second).

        The only constraint is weight >= 0.

        Args:
            dim:    YUIDimension.YD_HORIZ or YUIDimension.YD_VERT.
            weight: Non-negative integer. Negative values are clamped to 0.
        """
        try:
            w = max(0, int(weight))
        except (TypeError, ValueError):
            w = 0

        if dim == YUIDimension.YD_HORIZ:
            self._weight_horiz = w
        else:
            self._weight_vert = w
    
    def setNotify(self, notify=True):
        self._notify = notify
    
    def notify(self):
        return self._notify
    
    def autoShortcut(self):
        return self._auto_shortcut
    
    def setAutoShortcut(self, auto_shortcut):
        self._auto_shortcut = auto_shortcut
    
    def functionKey(self):
        return self._function_key
    
    def setFunctionKey(self, fkey_no):
        self._function_key = fkey_no
    
    # Backend-specific methods to be implemented by concrete classes
    def _set_backend_enabled(self, enabled):
        pass
    
    def _create_backend_widget(self):
        pass
    
    def get_backend_widget(self):
        if self._backend_widget is None:
            self._create_backend_widget()
        return self._backend_widget

class YSingleChildContainerWidget(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def child(self):
        '''
        Returns the only child of this single-child container, or None if no child is set.       
        '''
        return self.firstChild()

    def addChild(self, child):
        if self.hasChildren():
            raise YUIInvalidWidgetException("YSingleChildContainerWidget can only have one child")
        super().addChild(child)

class YSelectionWidget(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        self._selected_items = []
        self._label = ""
        self._icon_base_path = ""
    
    def label(self):
        return self._label
    
    def setLabel(self, new_label):
        self._label = new_label
    
    def addItem(self, item):
        if isinstance(item, str):
            item = YItem(item)
        self._items.append(item)

    def addItems(self, items):
        """Add multiple items to the selection widget."""
        for it in items:
            self.addItem(it)
    
    def deleteAllItems(self):
        self._items.clear()
        self._selected_items.clear()
    
    def itemsBegin(self):
        return iter(self._items)
    
    def itemsEnd(self):
        return iter([])
    
    def hasItems(self):
        return len(self._items) > 0
    
    def itemsCount(self):
        return len(self._items)
    
    def selectedItem(self):
        return self._selected_items[0] if self._selected_items else None
    
    def selectedItems(self):
        return self._selected_items
    
    def hasSelectedItem(self):
        return len(self._selected_items) > 0
    
    def selectItem(self, item, selected=True):
        if selected and item not in self._selected_items:
            self._selected_items.append(item)
        elif not selected and item in self._selected_items:
            self._selected_items.remove(item)

class YSimpleInputField(YWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = ""
        self._label = ""
    
    def value(self):
        return self._value
    
    def setValue(self, text):
        self._value = text
    
    def label(self):
        return self._label
    
    def setLabel(self, label):
        self._label = label

class YHtmlViewBase(YWidget):
    """Shared model of the read-only YHtmlView widget.

    Every backend subclasses this and only implements how sanitized content is
    shown (``_apply_content``) and, if needed, how links are encoded
    (``_link_href``).  Hardening is never left to a backend: content always
    goes through ``yui_html.sanitize_html()`` first, so scripts, active
    content and (by default) remote loads are gone before any engine sees it.

    Links never navigate.  Activating one stores its original target, readable
    with lastActivatedUrl(), and posts a YWidgetEvent with reason Activated
    (when notify() is on).
    """

    def __init__(self, parent=None, html: str = ""):
        # Attributes first: addChild() on the parent may render us immediately.
        self._html = html or ""
        self._base_policy = YHtmlBasePolicy.NoBase
        self._allow_remote = False
        self._cid_resolver = None
        self._last_url = None
        self._rendered = None
        super().__init__(parent)
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)

    def widgetClass(self):
        return "YHtmlView"

    def setHtml(self, html: str, base_policy: YHtmlBasePolicy = YHtmlBasePolicy.NoBase):
        """Show *html* (untrusted).  *base_policy* is a YHtmlBasePolicy."""
        self._html = html or ""
        self._base_policy = base_policy if isinstance(base_policy, YHtmlBasePolicy) else YHtmlBasePolicy.NoBase
        self._content_changed()

    def html(self) -> str:
        """The HTML last passed to setHtml(), before sanitizing."""
        return self._html

    def basePolicy(self) -> YHtmlBasePolicy:
        return self._base_policy

    def setValue(self, html: str):
        """Alias of setHtml() keeping the current base policy."""
        self.setHtml(html, self._base_policy)

    def value(self) -> str:
        return self._html

    def setAllowRemote(self, allow: bool = True):
        """Allow (True) or block (False, default) remote images and CSS."""
        allow = bool(allow)
        if allow != self._allow_remote:
            self._allow_remote = allow
            self._content_changed()

    def allowRemote(self) -> bool:
        return self._allow_remote

    def remoteContentBlocked(self) -> bool:
        """True if the current content tried to load remote resources that
        were blocked (lets an application offer "show remote content")."""
        return self._sanitized().remote_blocked > 0

    def setCidResolver(self, resolver):
        """Set callable(content_id) -> (bytes, mime) | None for ``cid:`` images.

        Only raster image types are inlined; None removes the resolver.
        """
        self._cid_resolver = resolver if callable(resolver) else None
        self._content_changed()

    def cidResolver(self):
        return self._cid_resolver

    def lastActivatedUrl(self):
        """Original target of the last activated link, or None."""
        return self._last_url

    # -- backend hooks ------------------------------------------------------

    def _apply_content(self):
        """Push the (re)sanitized content to the backend widget."""
        pass

    def _link_href(self, index: int) -> str:
        """href written into the rendered HTML for the index-th link."""
        return f"{_yui_html.LINK_PREFIX}{index}"

    @staticmethod
    def _link_index(url) -> Optional[int]:
        """Link index encoded in an activated URL, or None."""
        return _yui_html.link_index_from_url(url)

    def _text_lines(self) -> list:
        """Current content flattened to lines of styled runs (engine-less
        backends); see yui_html.html_to_lines()."""
        return _yui_html.html_to_lines(self._sanitized().body)

    def _text_pango(self) -> str:
        """Current content as Pango markup with ``<a href>`` links."""
        return _yui_html.lines_to_pango(self._text_lines(), self._link_href)

    def _text_simple_html(self, href=None) -> str:
        """Current content as minimal b/i/u/a/br HTML."""
        return _yui_html.lines_to_simple_html(self._text_lines(), href or self._link_href)

    # -- shared internals ---------------------------------------------------

    def _content_changed(self):
        self._rendered = None
        self._apply_content()

    def _sanitized(self):
        """Current yui_html.SanitizedHtml, computed on first use."""
        rendered = self._rendered
        if rendered is None:
            rendered = _yui_html.sanitize_html(
                self._html,
                allow_remote=self._allow_remote,
                cid_resolver=self._cid_resolver,
                link_href=self._link_href,
                resolve_base=self._base_policy == YHtmlBasePolicy.DocumentBase,
            )
            self._rendered = rendered
        return rendered

    def _activate_link(self, index) -> bool:
        """Report the index-th link of the current content as activated."""
        rendered = self._rendered
        try:
            index = int(index)
        except (TypeError, ValueError):
            return False
        if rendered is None or not 0 <= index < len(rendered.links):
            return False
        self._last_url = rendered.links[index]
        if self.notify():
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.Activated))
        return True

class YChartBase(YWidget):
    """Shared base of the chart widgets (YChartPie, YChartBar).

    Holds what every chart has: a title, a legend position, the color
    palette, input validation, value formatting and the Activated event.
    Every model change ends in ``_apply_chart()``, the single backend
    redraw hook.  Charts are stretchable in both directions.
    """

    # Okabe-Ito colorblind-safe palette (black replaced by grey so it stays
    # visible on dark themes).  Cycled for entries without a custom color.
    PALETTE = (
        "#e69f00", "#56b4e9", "#009e73", "#f0e442",
        "#0072b2", "#d55e00", "#cc79a7", "#999999",
    )

    _COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

    def __init__(self, parent=None, label: str = ""):
        # Attributes first: addChild() on the parent may render us immediately.
        self._label = "" if label is None else str(label)
        self._legend_position = YChartLegendPosition.Right
        super().__init__(parent)
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)

    # -- validation ---------------------------------------------------------

    @staticmethod
    def _check_number(value, allow_negative: bool = False, what: str = "value") -> float:
        if isinstance(value, bool):
            raise TypeError(f"{what} must be a number, not bool")
        value = float(value)
        if not math.isfinite(value):
            raise ValueError(f"{what} must be finite, got {value!r}")
        if value < 0 and not allow_negative:
            raise ValueError(f"{what} must be >= 0, got {value!r}")
        return value

    @staticmethod
    def _check_color(color):
        """``"#rrggbb"`` normalized to lowercase, or None ("use the palette")."""
        if color is None or color == "":
            return None
        if not isinstance(color, str) or not YChartBase._COLOR_RE.match(color):
            raise ValueError(f"color must be '#rrggbb', got {color!r}")
        return color.lower()

    @staticmethod
    def _check_index_in(index, count: int, what: str = "index") -> int:
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError(f"{what} must be an int")
        if not 0 <= index < count:
            raise IndexError(f"{what} {index} out of range")
        return index

    # -- title and legend ---------------------------------------------------

    def setLabel(self, label: str):
        self._label = "" if label is None else str(label)
        self._apply_chart()

    def label(self) -> str:
        return self._label

    def setLegendPosition(self, position: YChartLegendPosition):
        if not isinstance(position, YChartLegendPosition):
            raise TypeError("position must be a YChartLegendPosition")
        self._legend_position = position
        self._apply_chart()

    def legendPosition(self) -> YChartLegendPosition:
        return self._legend_position

    # -- backend hooks ------------------------------------------------------

    def _apply_chart(self):
        """Redraw the backend widget from the current model."""
        pass

    # -- shared internals ---------------------------------------------------

    def _palette_color(self, index: int) -> str:
        return self.PALETTE[index % len(self.PALETTE)]

    @staticmethod
    def _format_value(value: float) -> str:
        if value == int(value) and abs(value) < 1e15:
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def _post_activated(self):
        """Post YWidgetEvent(Activated) when notify() is on."""
        if self.notify():
            dlg = self.findDialog()
            if dlg is not None:
                dlg._post_event(YWidgetEvent(self, YEventReason.Activated))

class YChartSlice:
    """One slice of a YChartPie: label, non-negative value, optional color
    (``"#rrggbb"``, None means "use the palette") and an application payload.

    Read-only for applications: change slices through the YChartPie setters
    so the chart redraws.
    """

    def __init__(self, label="", value=0, color=None, data=None):
        self._label = "" if label is None else str(label)
        self._value = YChartPieBase._check_value(value)
        self._color = YChartPieBase._check_color(color)
        self._data = data

    def label(self) -> str:
        return self._label

    def value(self) -> float:
        return self._value

    def color(self):
        """Custom color as ``"#rrggbb"``, or None when the palette is used."""
        return self._color

    def data(self):
        return self._data

class YChartPieBase(YChartBase):
    """Shared model of the YChartPie widget.

    Holds the slices and does all the math (percentages, angles, hit test,
    legend text), so a backend only paints ``_geometry()`` / ``_legend_rows()``
    and reports clicks through ``_slice_clicked()``.  Title, legend position,
    palette and the redraw hook ``_apply_chart()`` come from YChartBase.

    Angles are in degrees, 0 at 12 o'clock, growing clockwise.

    Clicking a slice selects it (selectedSlice()) and posts a YWidgetEvent
    with reason Activated (when notify() is on).
    """

    MAX_DONUT_RATIO = 0.9

    def __init__(self, parent=None, label: str = ""):
        # Attributes first: addChild() on the parent may render us immediately.
        self._slices = []
        self._selected = -1
        self._show_percent = True
        self._donut_ratio = 0.0
        self._center_text = ""
        self._geometry_cache = None
        super().__init__(parent, label)

    def widgetClass(self):
        return "YChartPie"

    # -- validation ---------------------------------------------------------

    @staticmethod
    def _check_value(value) -> float:
        return YChartBase._check_number(value, False, "slice value")

    def _check_index(self, index) -> int:
        return self._check_index_in(index, len(self._slices), "slice index")

    # -- slices -------------------------------------------------------------

    def addSlice(self, label, value, color=None, data=None) -> int:
        """Append a slice and return its index."""
        self._slices.append(YChartSlice(label, value, color, data))
        self._chart_changed()
        return len(self._slices) - 1

    def setSlices(self, slices):
        """Replace all slices at once (one redraw).

        *slices* holds YChartSlice objects or ``(label, value[, color[, data]])``
        tuples.  Everything is validated before the chart changes.
        """
        new = []
        for s in slices or ():
            if isinstance(s, YChartSlice):
                new.append(s)
            else:
                new.append(YChartSlice(*s))
        self._slices = new
        self._selected = -1
        self._chart_changed()

    def setSliceValue(self, index: int, value):
        s = self._slices[self._check_index(index)]
        s._value = self._check_value(value)
        self._chart_changed()

    def setSliceLabel(self, index: int, label):
        s = self._slices[self._check_index(index)]
        s._label = "" if label is None else str(label)
        self._chart_changed()

    def setSliceColor(self, index: int, color):
        """Set a custom ``"#rrggbb"`` color, or None to go back to the palette."""
        s = self._slices[self._check_index(index)]
        s._color = self._check_color(color)
        self._chart_changed()

    def removeSlice(self, index: int):
        del self._slices[self._check_index(index)]
        if self._selected == index:
            self._selected = -1
        elif self._selected > index:
            self._selected -= 1
        self._chart_changed()

    def deleteAllSlices(self):
        self._slices = []
        self._selected = -1
        self._chart_changed()

    def sliceCount(self) -> int:
        return len(self._slices)

    def slice(self, index: int) -> YChartSlice:
        return self._slices[self._check_index(index)]

    def sliceColor(self, index: int) -> str:
        """Color the slice is drawn with: custom one, else from PALETTE."""
        s = self._slices[self._check_index(index)]
        return s._color or self._palette_color(index)

    def total(self) -> float:
        return sum(s._value for s in self._slices)

    def slicePercent(self, index: int) -> float:
        """Share of the slice in the total, 0..100 (0 when the total is 0)."""
        s = self._slices[self._check_index(index)]
        total = self.total()
        return s._value * 100.0 / total if total > 0 else 0.0

    # -- look ---------------------------------------------------------------

    def setShowPercent(self, show: bool = True):
        """Show (True, default) or hide the percent column of the legend."""
        self._show_percent = bool(show)
        self._apply_chart()

    def showPercent(self) -> bool:
        return self._show_percent

    def setDonutRatio(self, ratio: float):
        """Inner hole radius as a fraction of the outer one; 0 = full pie.

        Clamped to 0..MAX_DONUT_RATIO.
        """
        ratio = float(ratio)
        if not math.isfinite(ratio):
            raise ValueError("donut ratio must be finite")
        self._donut_ratio = min(max(ratio, 0.0), self.MAX_DONUT_RATIO)
        self._apply_chart()

    def donutRatio(self) -> float:
        return self._donut_ratio

    def setCenterText(self, text: str):
        """Text in the donut hole (not shown when donutRatio() is 0)."""
        self._center_text = "" if text is None else str(text)
        self._apply_chart()

    def centerText(self) -> str:
        return self._center_text

    # -- selection ----------------------------------------------------------

    def selectedSlice(self) -> int:
        """Index of the selected (last clicked) slice, -1 if none."""
        return self._selected

    def setSelectedSlice(self, index: int):
        """Highlight *index* (-1 clears) without posting an event."""
        if index != -1:
            self._check_index(index)
        self._selected = index
        self._apply_chart()

    # -- shared internals ---------------------------------------------------

    def _chart_changed(self):
        self._geometry_cache = None
        self._apply_chart()

    def _geometry(self) -> list:
        """Drawable slices as ``(index, start_deg, sweep_deg, color)``.

        Zero-value slices are left out; empty when the total is 0 (backends
        then draw an empty ring and "No data").
        """
        geom = self._geometry_cache
        if geom is None:
            geom = []
            total = self.total()
            if total > 0:
                start = 0.0
                for i, s in enumerate(self._slices):
                    if s._value <= 0:
                        continue
                    sweep = s._value * 360.0 / total
                    geom.append((i, start, sweep, self.sliceColor(i)))
                    start += sweep
            self._geometry_cache = geom
        return geom

    def _slice_at(self, dx: float, dy: float, radius: float) -> int:
        """Slice under a point at (*dx*, *dy*) from the center, screen
        coordinates (y grows downward), on a pie of *radius*; -1 if none."""
        if radius <= 0:
            return -1
        r = math.hypot(dx, dy)
        if r > radius or r < radius * self._donut_ratio:
            return -1
        angle = math.degrees(math.atan2(dx, -dy)) % 360.0
        for index, start, sweep, _color in self._geometry():
            if start <= angle < start + sweep:
                return index
        geom = self._geometry()
        # Rounding can leave angle a hair past the last slice end.
        return geom[-1][0] if geom else -1

    def _legend_rows(self) -> list:
        """Legend rows as ``(index, label, value_text, percent_text, color)``;
        percent_text is "" when showPercent() is off."""
        total = self.total()
        rows = []
        for i, s in enumerate(self._slices):
            pct = ""
            if self._show_percent:
                pct = f"{(s._value * 100.0 / total) if total > 0 else 0.0:.1f}%"
            rows.append((i, s._label, self._format_value(s._value), pct,
                         self.sliceColor(i)))
        return rows

    def _slice_tooltip(self, index: int) -> str:
        """Hover text for a slice: "label: value (pct%)"."""
        s = self._slices[index]
        return (f"{s._label}: {self._format_value(s._value)} "
                f"({self.slicePercent(index):.1f}%)")

    def _slice_clicked(self, index) -> bool:
        """Select the index-th slice and report it as activated."""
        try:
            index = int(index)
        except (TypeError, ValueError):
            return False
        if not 0 <= index < len(self._slices):
            return False
        self._selected = index
        self._apply_chart()
        self._post_activated()
        return True

class YChartBarBase(YChartBase):
    """Shared model of the YChartBar widget: categories x series.

    Each category is one group of bars, one bar per series; series carry the
    legend entries and colors.  Bars are side by side (grouped) or piled up
    (setStacked(True)); values may be negative (bars below the zero line).

    All the math lives here so backends only map units to pixels:

    - ``_value_axis()`` -> (vmin, vmax, ticks): "nice" range including 0;
    - ``_bar_geometry()`` -> (c, s, u0, u1, v0, v1, color) per non-zero bar,
      where u0..u1 is the position along the category axis in 0..1 and
      v0 -> v1 the data interval from the baseline to the bar end;
    - ``_bar_at(u, v)`` -> (c, s) hit test in the same units.

    Clicking a bar selects (category, series) and posts a YWidgetEvent with
    reason Activated (when notify() is on).
    """

    GROUP_FILL = 0.8        # share of a category slot covered by its bars
    _TICK_TARGET = 5        # wanted number of axis steps

    def __init__(self, parent=None, label: str = ""):
        # Attributes first: addChild() on the parent may render us immediately.
        self._series = []           # [[name, color or None]]
        self._categories = []       # [label]
        self._rows = []             # [category][series] -> float
        self._orientation = YChartBarOrientation.Vertical
        self._stacked = False
        self._show_values = False
        self._show_grid = True
        self._sel = (-1, -1)
        self._geometry_cache = None
        self._axis_cache = None
        super().__init__(parent, label)

    def widgetClass(self):
        return "YChartBar"

    # -- validation ---------------------------------------------------------

    @staticmethod
    def _check_bar_value(value) -> float:
        return YChartBase._check_number(value, True, "bar value")

    def _check_series(self, s) -> int:
        return self._check_index_in(s, len(self._series), "series index")

    def _check_category(self, c) -> int:
        return self._check_index_in(c, len(self._categories), "category index")

    def _check_row(self, values, width: int) -> list:
        values = [] if values is None else [self._check_bar_value(v) for v in values]
        if len(values) > width:
            raise ValueError(f"{len(values)} values for {width} series")
        return values + [0.0] * (width - len(values))

    @staticmethod
    def _series_entry(item) -> list:
        if isinstance(item, (tuple, list)):
            if not 1 <= len(item) <= 2:
                raise ValueError("series must be name or (name, color)")
            name, color = item[0], (item[1] if len(item) > 1 else None)
        else:
            name, color = item, None
        return ["" if name is None else str(name), YChartBase._check_color(color)]

    # -- series -------------------------------------------------------------

    def addSeries(self, name, color=None) -> int:
        """Append a series (a bar in every category, value 0); return its index."""
        self._series.append(self._series_entry((name, color)))
        for row in self._rows:
            row.append(0.0)
        self._chart_changed()
        return len(self._series) - 1

    def setSeriesName(self, s: int, name):
        self._series[self._check_series(s)][0] = "" if name is None else str(name)
        self._chart_changed()

    def seriesName(self, s: int) -> str:
        return self._series[self._check_series(s)][0]

    def setSeriesColor(self, s: int, color):
        """Set a custom ``"#rrggbb"`` color, or None to go back to the palette."""
        self._series[self._check_series(s)][1] = self._check_color(color)
        self._chart_changed()

    def seriesColor(self, s: int) -> str:
        """Color the series is drawn with: custom one, else from PALETTE."""
        return self._series[self._check_series(s)][1] or self._palette_color(s)

    def removeSeries(self, s: int):
        self._check_series(s)
        del self._series[s]
        for row in self._rows:
            del row[s]
        c, sel = self._sel
        if sel == s:
            self._sel = (-1, -1)
        elif sel > s:
            self._sel = (c, sel - 1)
        self._chart_changed()

    def seriesCount(self) -> int:
        return len(self._series)

    # -- categories ---------------------------------------------------------

    def addCategory(self, label, values=None) -> int:
        """Append a category; *values* holds one value per series (missing = 0).
        Returns its index."""
        row = self._check_row(values, len(self._series))
        self._categories.append("" if label is None else str(label))
        self._rows.append(row)
        self._chart_changed()
        return len(self._categories) - 1

    def setCategoryLabel(self, c: int, label):
        self._categories[self._check_category(c)] = "" if label is None else str(label)
        self._chart_changed()

    def categoryLabel(self, c: int) -> str:
        return self._categories[self._check_category(c)]

    def removeCategory(self, c: int):
        self._check_category(c)
        del self._categories[c]
        del self._rows[c]
        sel, s = self._sel
        if sel == c:
            self._sel = (-1, -1)
        elif sel > c:
            self._sel = (sel - 1, s)
        self._chart_changed()

    def categoryCount(self) -> int:
        return len(self._categories)

    # -- values -------------------------------------------------------------

    def setValue(self, c: int, s: int, value):
        self._check_category(c)
        self._check_series(s)
        self._rows[c][s] = self._check_bar_value(value)
        self._chart_changed()

    def value(self, c: int, s: int) -> float:
        self._check_category(c)
        self._check_series(s)
        return self._rows[c][s]

    def categoryTotal(self, c: int) -> float:
        """Sum of the category values over all series."""
        return sum(self._rows[self._check_category(c)])

    def setData(self, categories, series, rows=None):
        """Replace everything at once (one redraw, selection cleared).

        *categories*: labels; *series*: names or ``(name, color)``;
        *rows*: ``rows[c][s]`` values, short or missing rows padded with 0.
        Everything is validated before the chart changes.
        """
        new_series = [self._series_entry(item) for item in (series or ())]
        new_categories = ["" if c is None else str(c) for c in (categories or ())]
        rows = list(rows or ())
        if len(rows) > len(new_categories):
            raise ValueError(f"{len(rows)} rows for {len(new_categories)} categories")
        rows += [None] * (len(new_categories) - len(rows))
        new_rows = [self._check_row(r, len(new_series)) for r in rows]
        self._series, self._categories, self._rows = new_series, new_categories, new_rows
        self._sel = (-1, -1)
        self._chart_changed()

    def deleteAllData(self):
        """Remove every category and series."""
        self.setData((), (), ())

    # -- look ---------------------------------------------------------------

    def setOrientation(self, orientation: YChartBarOrientation):
        if not isinstance(orientation, YChartBarOrientation):
            raise TypeError("orientation must be a YChartBarOrientation")
        self._orientation = orientation
        self._apply_chart()

    def orientation(self) -> YChartBarOrientation:
        return self._orientation

    def setStacked(self, stacked: bool = True):
        """Pile the series of a category (True) instead of side by side."""
        self._stacked = bool(stacked)
        self._chart_changed()

    def stacked(self) -> bool:
        return self._stacked

    def setShowValues(self, show: bool = True):
        """Draw each value at the end of its bar (default False)."""
        self._show_values = bool(show)
        self._apply_chart()

    def showValues(self) -> bool:
        return self._show_values

    def setShowGrid(self, show: bool = True):
        """Draw gridlines at the axis ticks (default True); the axis stays."""
        self._show_grid = bool(show)
        self._apply_chart()

    def showGrid(self) -> bool:
        return self._show_grid

    # -- selection ----------------------------------------------------------

    def selectedCategory(self) -> int:
        """Category of the selected (last clicked) bar, -1 if none."""
        return self._sel[0]

    def selectedSeries(self) -> int:
        """Series of the selected (last clicked) bar, -1 if none."""
        return self._sel[1]

    def setSelectedBar(self, c: int, s: int):
        """Highlight bar (*c*, *s*) without posting an event; (-1, -1) clears."""
        if (c, s) != (-1, -1):
            self._check_category(c)
            self._check_series(s)
        self._sel = (c, s)
        self._apply_chart()

    # -- shared internals ---------------------------------------------------

    def _chart_changed(self):
        self._geometry_cache = None
        self._axis_cache = None
        self._apply_chart()

    @staticmethod
    def _nice_step(raw: float) -> float:
        """1/2/5 x 10^n step nearest to *raw* (so the axis gets ~4-8 steps)."""
        exp = math.floor(math.log10(raw))
        base = 10.0 ** exp
        f = raw / base
        if f < 1.5:
            return base
        if f < 3.0:
            return 2.0 * base
        if f < 7.0:
            return 5.0 * base
        return 10.0 * base

    def _data_range(self):
        lo = hi = 0.0
        for row in self._rows:
            if self._stacked:
                lo = min(lo, sum(v for v in row if v < 0))
                hi = max(hi, sum(v for v in row if v > 0))
            else:
                for v in row:
                    lo = min(lo, v)
                    hi = max(hi, v)
        return lo, hi

    def _value_axis(self):
        """``(vmin, vmax, ticks)``: data range with 0, rounded to nice steps.

        Empty or all-zero data gives 0..1.
        """
        axis = self._axis_cache
        if axis is None:
            lo, hi = self._data_range()
            if hi - lo <= 0:
                lo, hi = 0.0, 1.0
            step = self._nice_step((hi - lo) / self._TICK_TARGET)
            vmin = math.floor(lo / step + 1e-9) * step
            vmax = math.ceil(hi / step - 1e-9) * step
            digits = max(0, -int(math.floor(math.log10(step))) + 1)
            n = int(round((vmax - vmin) / step))
            ticks = [round(vmin + i * step, digits) or 0.0 for i in range(n + 1)]
            axis = (round(vmin, digits) or 0.0, round(vmax, digits) or 0.0, ticks)
            self._axis_cache = axis
        return axis

    def _bar_geometry(self) -> list:
        """Drawable bars as ``(c, s, u0, u1, v0, v1, color)``.

        u0..u1: position along the category axis, 0..1 (category c owns the
        slot c/n..(c+1)/n).  v0 -> v1: from the bar baseline to its end, in
        data units (grouped: 0 -> value; stacked: running sums kept apart for
        positive and negative values).  Zero values are left out.
        """
        geom = self._geometry_cache
        if geom is None:
            geom = []
            n, k = len(self._categories), len(self._series)
            if n and k:
                slot = 1.0 / n
                group = slot * self.GROUP_FILL
                pad = (slot - group) / 2.0
                colors = [self.seriesColor(s) for s in range(k)]
                for c, row in enumerate(self._rows):
                    left = c * slot + pad
                    pos = neg = 0.0
                    for s, v in enumerate(row):
                        if v == 0:
                            continue
                        if self._stacked:
                            u0, u1 = left, left + group
                            if v > 0:
                                v0, pos = pos, pos + v
                                v1 = pos
                            else:
                                v0, neg = neg, neg + v
                                v1 = neg
                        else:
                            w = group / k
                            u0, u1 = left + s * w, left + (s + 1) * w
                            v0, v1 = 0.0, v
                        geom.append((c, s, u0, u1, v0, v1, colors[s]))
            self._geometry_cache = geom
        return geom

    def _bar_at(self, u: float, v: float):
        """Bar at category-axis position *u* (0..1) and data value *v*;
        ``(-1, -1)`` if none."""
        for c, s, u0, u1, v0, v1, _color in self._bar_geometry():
            if u0 <= u < u1 and min(v0, v1) <= v <= max(v0, v1):
                return c, s
        return -1, -1

    def _category_at(self, u: float) -> int:
        """Category whose slot contains *u* (0..1), -1 if none."""
        n = len(self._categories)
        if n == 0 or not 0 <= u < 1:
            return -1
        return min(n - 1, int(u * n))

    @staticmethod
    def _format_tick(value: float) -> str:
        """Compact axis label: 0, 2.5, 1.5k, 20M, -3G."""
        if value == 0:
            return "0"
        a = abs(value)
        for limit, suffix in ((1e12, "T"), (1e9, "G"), (1e6, "M"), (1e3, "k")):
            if a >= limit:
                return f"{value / limit:.3g}{suffix}"
        return f"{value:.6g}"

    def _value_text(self, c: int, s: int) -> str:
        return self._format_value(self._rows[c][s])

    def _bar_tooltip(self, c: int, s: int) -> str:
        """Hover text: "category · series: value" (series omitted if unnamed)."""
        name = self._series[s][0]
        head = f"{self._categories[c]} \u00b7 {name}" if name else self._categories[c]
        return f"{head}: {self._value_text(c, s)}"

    def _legend_rows(self) -> list:
        """Legend rows as ``(series index, name, color)``."""
        return [(s, entry[0], self.seriesColor(s)) for s, entry in enumerate(self._series)]

    def _bar_clicked(self, c, s) -> bool:
        """Select bar (*c*, *s*) and report it as activated."""
        try:
            c, s = int(c), int(s)
        except (TypeError, ValueError):
            return False
        if not (0 <= c < len(self._categories) and 0 <= s < len(self._series)):
            return False
        self._sel = (c, s)
        self._apply_chart()
        self._post_activated()
        return True

class YItem:
    def __init__(self, label, selected=False, icon_name=""):
        self._label = label
        self._selected = selected
        self._icon_name = icon_name
        self._index = 0
        self._data = None
    
    def label(self):
        return self._label
    
    def setLabel(self, new_label):
        self._label = new_label
    
    def selected(self):
        return self._selected
    
    def setSelected(self, selected=True):
        self._selected = selected
    
    def iconName(self):
        return self._icon_name
    
    def hasIconName(self):
        return bool(self._icon_name)
    
    def setIconName(self, new_icon_name):
        self._icon_name = new_icon_name
    
    def index(self):
        return self._index
    
    def setIndex(self, index):
        self._index = index
    
    def data(self):
        return self._data
    
    def setData(self, new_data):
        self._data = new_data

class YMenuItem:
    """Lightweight menu item model for backend-agnostic use.

    Supports label, icon name, enabled state and hierarchical children
    (submenus and items). Backends may attach platform-specific references
    via `_backend_ref` for synchronization.
    """
    def __init__(self, label: str, icon_name: str = "", enabled: bool = True, is_menu: bool = False, is_separator: bool = False):
        self._is_separator = bool(is_separator)
        self._label = "-" if self._is_separator else str(label)
        self._icon_name = str(icon_name) if icon_name else ""
        self._enabled = False if self._is_separator else bool(enabled)
        self._is_menu = False if self._is_separator else bool(is_menu)
        # visible flag (backends should respect this when rendering)
        self._visible = True
        self._children = []  # list of YMenuItem
        self._parent = None
        self._backend_ref = None  # optional backend-specific handle

    def label(self) -> str:
        return self._label

    def setLabel(self, new_label: str):
        self._label = str(new_label)

    def iconName(self) -> str:
        return self._icon_name

    def setIconName(self, new_icon_name: str):
        self._icon_name = str(new_icon_name) if new_icon_name else ""

    def enabled(self) -> bool:
        return bool(self._enabled)

    def setEnabled(self, on: bool = True):
        self._enabled = bool(on)

    def visible(self) -> bool:
        return bool(self._visible)

    def setVisible(self, on: bool = True):
        self._visible = bool(on)
        for child in self._children:
            child.setVisible(on)

    def isMenu(self) -> bool:
        return bool(self._is_menu)

    def isSeparator(self) -> bool:
        return bool(self._is_separator)
    
    def parentItem(self):
        return self._parent
    
    def hasChildren(self):
        return len(self._children) > 0

    def childrenBegin(self):
        return iter(self._children)

    def childrenEnd(self):
        return iter([])

    def hasChildren(self) -> bool:
        return len(self._children) > 0

    def addItem(self, label: str, icon_name: str = ""):
        child = YMenuItem(label, icon_name, enabled=True, is_menu=False)
        child._parent = self
        child.setVisible(self.visible())
        self._children.append(child)
        return child

    def addMenu(self, label: str, icon_name: str = ""):
        child = YMenuItem(label, icon_name, enabled=True, is_menu=True)
        child._parent = self
        child.setVisible(self.visible())
        self._children.append(child)
        return child

    def addSeparator(self):
        # Represent separator as a disabled item with label "-"; backends can special-case it.
        sep = YMenuItem("-", is_menu=False, enabled=False, is_separator=True)
        sep._parent = self
        self._children.append(sep)
        return sep

class YTreeItem(YItem):
    def __init__(self, label: str, parent: Optional["YTreeItem"] = None, selected: Optional[bool] = False, is_open: bool = False, icon_name: str = ""):
        ''' YTreeItem represents an item in a tree structure.
            It can have child items and can be expanded or collapsed.'''
        super().__init__(label, selected, icon_name)
        self._children = []
        self._is_open = is_open
        self._parent_item = parent
        if parent:
            parent.addChild(self)
    
    def parentItem(self):
        return self._parent_item
    
    def hasChildren(self):
        return len(self._children) > 0
    
    def childrenBegin(self):
        return iter(self._children)
    
    def childrenEnd(self):
        return iter([])
    
    def addChild(self, item):
        if isinstance(item, str):
            item = YTreeItem(item)
        self._children.append(item)
        item._parent_item = self
        return item
    
    def isOpen(self):
        return self._is_open
    

class YTableHeader:
    """Helper class for table column properties.

    Tracks columns' header text, alignment and whether a column is a
    checkbox column.
    """
    def __init__(self):
        self._columns = []  # list of dicts: {'header': str, 'alignment': YAlignmentType, 'checkbox': bool}

    def addColumn(self, header, checkBox : Optional[bool] = False, alignment=YAlignmentType.YAlignBegin):
        """Add a column with header text and optional alignment (no checkbox)."""
        self._columns.append({'header': str(header), 'alignment': alignment, 'checkbox': bool(checkBox)})

    def columns(self):
        return len(self._columns)

    def hasColumn(self, column):
        return 0 <= int(column) < len(self._columns)

    def header(self, column):
        try:
            return self._columns[int(column)]['header']
        except Exception:
            return ""

    def isCheckboxColumn(self, column):
        try:
            return bool(self._columns[int(column)]['checkbox'])
        except Exception:
            return False

    def alignment(self, column):
        try:
            return self._columns[int(column)]['alignment']
        except Exception:
            return YAlignmentType.YAlignUnchanged


class YTableCell:
    """One cell (one column in one row) of a YTableItem.

    Supports label, optional icon name, optional sort key and an optional
    checkbox state. Cells can be created detached or with a parent/table
    assigned via `reparent()`.
    """
    def __init__(self, label: str = "", icon_name: str = "", sort_key: str = "", parent: Optional["YTableItem"] = None, column: int = -1, checked: Optional[bool] = None):
        self._label = label
        self._icon_name = icon_name
        self._sort_key = sort_key
        self._parent = parent
        self._column = column
        # checked: None means not-a-checkbox column; True/False represent checkbox state
        self._checked = checked

    def label(self):
        return self._label

    def setLabel(self, new_label: str):
        self._label = new_label

    def iconName(self):
        return self._icon_name

    def setIconName(self, new_icon_name: str):
        self._icon_name = new_icon_name

    def hasIconName(self):
        return bool(self._icon_name)

    def sortKey(self):
        return self._sort_key

    def hasSortKey(self):
        return bool(self._sort_key)

    def parent(self):
        return self._parent

    def column(self):
        return self._column

    def itemIndex(self):
        return self._parent.index() if self._parent is not None else -1

    def reparent(self, parent: "YTableItem", column: int):
        if self._parent is not None:
            raise Exception("Cell already has a parent")
        self._parent = parent
        self._column = column

    # checkbox API
    def setChecked(self, val: bool = True):
        self._checked = bool(val)

    def checked(self):
        return bool(self._checked) if self._checked is not None else False


class YTableItem(YTreeItem):
    """Table item (one row). Each item may contain multiple `YTableCell`.

    Provides convenience constructors and cell management similar to
    the C++ `YTableItem` while also supporting checkbox cells.
    """
    def __init__(self, label: str = "", parent: Optional["YTreeItem"] = None, is_open: bool = False, icon_name: str = ""):
        super().__init__(label, parent, False, is_open, icon_name)
        self._cells = []  # list of YTableCell

    def addCell(self, cell_or_label, icon_name: str = "", sort_key: str = ""):
        """Add a cell instance or create one from label/icon/sort_key.
        If a boolean is passed as first arg, treat it as a checkbox cell value.
        """
        if isinstance(cell_or_label, YTableCell):
            cell = cell_or_label
        else:
            # allow boolean-only constructor for checkbox column
            if isinstance(cell_or_label, bool):
                cell = YTableCell("", "", "", parent=self, column=len(self._cells), checked=cell_or_label)
            else:
                cell = YTableCell(str(cell_or_label), icon_name, sort_key, parent=self, column=len(self._cells))
        # set parent/column and append
        try:
            cell.reparent(self, len(self._cells))
        except Exception:
            # already parented; update column if needed
            cell._column = len(self._cells)
            cell._parent = self
        self._cells.append(cell)

    def addCells(self, *labels):
        for lbl in labels:
            self.addCell(lbl)

    def deleteCells(self):
        self._cells = []

    def cellsBegin(self):
        return iter(self._cells)

    def cellsEnd(self):
        return iter([])

    def cell(self, index: int):
        if not self.hasCell(index):
            return None
        try:
            return self._cells[index]
        except Exception:
            return None

    def cellCount(self):
        return len(self._cells)

    def hasCell(self, index: int):
        return 0 <= index < len(self._cells)

    def label(self, index: int = 0):
        if not self.hasCell(index):
            return ""
        c = self.cell(index)
        return c.label() if c is not None else ""
    
    def checked(self, index: int = 0):
        if not self.hasCell(index):
            return False
        c = self.cell(index)
        return c.checked() if c is not None else False

    def iconName(self, index: int = 0):
        c = self.cell(index)
        return c.iconName() if c is not None else ""

    def hasIconName(self, index: int = 0):
        c = self.cell(index)
        return c.hasIconName() if c is not None else False

    def debugLabel(self):
        return f"{super().debugLabel()}[cells={self.cellCount()}]"

# Property system
class YPropertyType(Enum):
    YUnknownPropertyType = 0
    YOtherProperty = 1
    YStringProperty = 2
    YBoolProperty = 3
    YIntegerProperty = 4

class YProperty:
    def __init__(self, name, prop_type, is_readonly=False):
        self._name = name
        self._type = prop_type
        self._is_readonly = is_readonly
    
    def name(self):
        return self._name
    
    def type(self):
        return self._type
    
    def isReadOnly(self):
        return self._is_readonly

class YPropertyValue:
    def __init__(self, value=None, prop_type=YPropertyType.YUnknownPropertyType):
        self._value = value
        self._type = prop_type
    
    def type(self):
        return self._type
    
    def stringVal(self):
        return str(self._value) if self._value else ""
    
    def boolVal(self):
        return bool(self._value)
    
    def integerVal(self):
        return int(self._value) if self._value else 0

class YPropertySet:
    def __init__(self):
        self._properties = {}
    
    def add(self, prop):
        self._properties[prop.name()] = prop
    
    def contains(self, name):
        return name in self._properties
    
    def isEmpty(self):
        return len(self._properties) == 0

class YShortcut:
    def __init__(self, widget):
        self._widget = widget
        self._shortcut = ''
        self._conflict = False
    
    def widget(self):
        return self._widget
    
    def shortcutString(self):
        return self._shortcut
    
    def setShortcut(self, new_shortcut):
        self._shortcut = new_shortcut
    
    def conflict(self):
        return self._conflict
    
    def setConflict(self, conflict=True):
        self._conflict = conflict
