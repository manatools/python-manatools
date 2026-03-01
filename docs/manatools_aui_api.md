# manatools AUI — Complete API Reference

## Overview

`manatools.aui` is a backend-agnostic UI abstraction layer inspired by libyui. It supports three backends: **GTK4**, **Qt6 (PySide6)** and **NCurses**. Application code uses a single API regardless of the backend in use.

```python
from manatools.aui.yui import YUI, YUI_ui
```

---

## 1. Backend Selection and Initialization

The backend is selected at startup by reading the `YUI_BACKEND` environment variable. Accepted values are `gtk`, `qt` and `ncurses` (case-insensitive). When the variable is not set, backends are probed in this order: Qt → GTK → NCurses.

```python
import os
os.environ["YUI_BACKEND"] = "gtk"   # force GTK backend

from manatools.aui.yui import YUI, YUI_ui
```

### Obtaining the UI and application objects

```python
ui  = YUI.ui()          # YUI singleton (also: YUI_ui())
app = YUI.app()         # backend application object
# aliases: YUI.application(), YUI.yApp()
factory = ui.widgetFactory()
```

### NCurses shutdown

For the NCurses backend, always call `ui.shutdown()` before the process exits to restore the terminal:

```python
ui = YUI_ui()
try:
    ...
finally:
    ui.shutdown()   # NCurses only; no-op on GUI backends
```

---

## 2. Enums

All enums are importable from `manatools.aui.yui` (they are re-exported from `yui_common`).

### YUIDimension

```python
class YUIDimension(Enum):
    YD_HORIZ  = 0   # Horizontal = 0 (alias)
    Horizontal = 0
    YD_VERT   = 1   # Vertical = 1 (alias)
    Vertical  = 1
```

### YAlignmentType

```python
class YAlignmentType(Enum):
    YAlignUnchanged = 0   # do not force alignment
    YAlignBegin     = 1   # left / top
    YAlignEnd       = 2   # right / bottom
    YAlignCenter    = 3   # center
```

### YDialogType

```python
class YDialogType(Enum):
    YMainDialog   = 0
    YPopupDialog  = 1
    YWizardDialog = 2
```

### YDialogColorMode

```python
class YDialogColorMode(Enum):
    YDialogNormalColor = 0
    YDialogInfoColor   = 1
    YDialogWarnColor   = 2
```

### YEventType

```python
class YEventType(Enum):
    NoEvent       = 0
    WidgetEvent   = 1
    MenuEvent     = 2
    KeyEvent      = 3
    CancelEvent   = 4
    TimeoutEvent  = 5
```

### YEventReason

```python
class YEventReason(Enum):
    Activated         = 0
    ValueChanged      = 1
    SelectionChanged  = 2
```

### YCheckBoxState

```python
class YCheckBoxState(Enum):
    YCheckBox_dont_care = -1   # tri-state: indeterminate
    YCheckBox_off       = 0
    YCheckBox_on        = 1
```

### YButtonRole

```python
class YButtonRole(Enum):
    YCustomButton = 0
    YOKButton     = 1
    YCancelButton = 2
    YHelpButton   = 3
```

---

## 3. Exception Classes

```python
class YUIException(Exception): ...
class YUIWidgetNotFoundException(YUIException): ...
class YUINoDialogException(YUIException): ...
class YUIInvalidWidgetException(YUIException): ...
```

All exceptions derive from `YUIException`. `YUINoDialogException` is raised when dialog-level operations (e.g. `currentDialog()`) are called with no open dialog.

---

## 4. Event Classes

All event objects are returned by `dialog.waitForEvent()` or `dialog.pollEvent()`.

### YEvent (base)

```python
ev.eventType()  -> YEventType
ev.widget()     -> YWidget | None   # widget that generated the event
ev.reason()     -> YEventReason | None
ev.serial()     -> int
```

### YWidgetEvent

Generated when the user interacts with a widget (button press, field change, etc.).

```python
isinstance(ev, YWidgetEvent)  # True when ev.eventType() == YEventType.WidgetEvent
ev.widget()   # the widget
ev.reason()   # e.g. YEventReason.Activated
```

### YKeyEvent

```python
ev.keySymbol()   -> str   # e.g. "F1", "Return", "Escape"
ev.focusWidget() -> YWidget | None
```

### YMenuEvent

Generated when a menu item is activated.

```python
ev.item()  -> YMenuItem | None
ev.id()    -> str | None
```

### YTimeoutEvent

Fired when `waitForEvent(timeout_millisec)` times out before a user action.

```python
ev.eventType() == YEventType.TimeoutEvent
```

### YCancelEvent

Generated when the user closes the dialog via the window manager (close button, Escape, Ctrl-C in NCurses).

```python
ev.eventType() == YEventType.CancelEvent
```

---

## 5. YWidget Base API

Every widget returned by the factory inherits from `YWidget`. The methods below are available on all widgets regardless of backend.

### Identity

```python
w.id()             -> str    # auto-generated unique identifier
w.widgetClass()    -> str    # class name string (e.g. "YPushButton")
w.widgetPathName() -> str    # full path in widget hierarchy
w.debugLabel()     -> str    # human-readable label for debugging
```

### Tree navigation

```python
w.parent()         -> YWidget | None
w.hasParent()      -> bool
w.firstChild()     -> YWidget | None
w.lastChild()      -> YWidget | None
w.childrenCount()  -> int
w.hasChildren()    -> bool
w.addChild(child)
w.removeChild(child)
w.deleteChildren()          # remove all logical children
w.findDialog()     -> YWidget | None   # nearest ancestor dialog
```

### Enable / disable

```python
w.setEnabled(enabled: bool = True)
w.setDisabled()           # shortcut for setEnabled(False)
w.isEnabled() -> bool
```

### Visibility

```python
w.setVisible(visible: bool = True)
w.visible() -> bool
```

### Layout weight

Weights control how extra space is distributed among siblings in a container. The values are non-negative integers; what matters is the ratio between sibling weights.

```python
w.setWeight(dim: YUIDimension, weight: int)
w.weight(dim: YUIDimension) -> int
```

Example — split a VBox in a 2/3 : 1/3 ratio:

```python
top_widget.setWeight(YUIDimension.YD_VERT, 67)
bot_widget.setWeight(YUIDimension.YD_VERT, 33)
```

Weights of 0 (the default) mean the widget has no preference; allocation falls back to equal distribution or natural sizes.

### Stretchability

```python
w.setStretchable(dim: YUIDimension, stretch: bool)
w.stretchable(dim: YUIDimension) -> bool
```

A stretchable widget expands to fill available space in the given dimension. `setWeight` implies stretchability on that axis.

### Notifications

```python
w.setNotify(notify: bool = True)
w.notify() -> bool
```

When `notify` is `True` (default), the widget posts a `YWidgetEvent` each time its value or selection changes.

### Help text / tooltip

```python
w.setHelpText(text: str)
w.helpText() -> str
```

### Function key shortcut

```python
w.setFunctionKey(fkey_no: int)   # e.g. 1 → F1
w.functionKey() -> int
```

---

## 6. Dialog API

Dialogs are created via the factory (see §7) and manage the event loop.

### Static helpers

```python
dialog.currentDialog(doThrow=True)   -> YDialog   # topmost open dialog
dialog.topmostDialog(doThrow=True)   -> YDialog   # alias
dialog.isTopmostDialog()             -> bool
```

### Instance methods

```python
dialog.open()                        # present the dialog (called automatically by waitForEvent)
dialog.isOpen()                      -> bool
dialog.destroy(doThrow=True)         # close and remove from stack
```

### Event loop

```python
ev = dialog.waitForEvent(timeout_millisec: int = 0) -> YEvent
```

Blocks until an event is available. If `timeout_millisec > 0` a `YTimeoutEvent` is delivered after the interval. In GTK and Qt the call runs a nested event-loop iteration so other windows remain responsive.

```python
ev = dialog.pollEvent() -> YEvent | None
```

Non-blocking variant; returns `None` immediately if no event is pending (not all backends guarantee full support).

### Typical event loop pattern

```python
while True:
    ev = dlg.waitForEvent()
    if ev.eventType() == YEventType.CancelEvent:
        break
    if ev.eventType() == YEventType.WidgetEvent:
        if ev.widget() == ok_btn:
            # handle OK
            break
dlg.destroy()
```

---

## 7. Application API

The object returned by `YUI.app()` is the backend-specific Application object. Obtain it with:

```python
app = YUI.app()          # YUI.application() and YUI.yApp() are aliases
```

### Title and icon

```python
app.setApplicationTitle(title: str)
app.applicationTitle() -> str

app.setApplicationIcon(icon_spec: str)   # theme name or file path
app.applicationIcon() -> str

app.setIconBasePath(path: str)           # prefix for icon resolution
app.iconBasePath() -> str
```

### Product and about metadata

```python
app.setProductName(name: str)    /  app.productName() -> str
app.setApplicationName(name: str) / app.applicationName() -> str
app.setVersion(version: str)     /  app.version() -> str
app.setAuthors(authors: str)     /  app.authors() -> str
app.setDescription(desc: str)    /  app.description() -> str
app.setLicense(text: str)        /  app.license() -> str
app.setCredits(credits: str)     /  app.credits() -> str
app.setInformation(info: str)    /  app.information() -> str
app.setLogo(path: str)           /  app.logo() -> str
```

### Mode and cursor

```python
app.isTextMode() -> bool          # True for NCurses backend
app.busyCursor()                  # show busy indicator (best-effort)
app.normalCursor()                # restore normal cursor
```

### File chooser helpers

Blocking helpers that return the selected path or `""` when canceled.

```python
app.askForExistingDirectory(startDir: str, headline: str) -> str
app.askForExistingFile(startWith: str, filter: str, headline: str) -> str
app.askForSaveFileName(startWith: str, filter: str, headline: str) -> str
```

`filter` is a semicolon-separated list of glob patterns (e.g. `"*.txt;*.md"`). GTK uses `Gtk.FileDialog` (GTK 4.10+, portal-aware); Qt uses `QFileDialog` (synchronous); NCurses renders an in-terminal browser overlay.

### Practical examples

```python
app = YUI.app()
app.setApplicationTitle("MyApp")
app.setIconBasePath("/usr/share/myapp/icons")
app.setApplicationIcon("myapp-icon")     # theme name or absolute path

fn = app.askForExistingFile("/home/user", "*.iso;*.img", "Open image")
if fn:
    print("Selected:", fn)
```

---

## 8. Widget Factory

The factory is obtained from the UI singleton:

```python
factory = YUI.ui().widgetFactory()
# or equivalently:
factory = YUI_ui().widgetFactory()
```

All `createXxx()` calls return a `YWidget` subclass with the backend widget attached. The parent argument must be an open dialog or a container widget that has already been added to a dialog.

### 8.1 Dialogs

```python
factory.createMainDialog(color_mode=YDialogColorMode.YDialogNormalColor) -> YDialog
factory.createPopupDialog(color_mode=YDialogColorMode.YDialogNormalColor) -> YDialog
```

A dialog is the root container. Every widget tree must start from a dialog. The `color_mode` hint changes the visual style on capable backends (GTK / Qt apply a tint; NCurses may adjust attribute sets).

### 8.2 Layout containers

```python
factory.createVBox(parent) -> YWidget   # stack children vertically
factory.createHBox(parent) -> YWidget   # stack children horizontally
```

Children add themselves to the container in creation order. To control how the space is divided, call `setWeight()` on each child after creation (see §5).

#### Paned (split pane)

```python
factory.createPaned(parent, dimension: YUIDimension = YUIDimension.YD_HORIZ) -> YWidget
```

A two-child split container with a resizable divider. `dimension` controls the split axis:
- `YUIDimension.YD_HORIZ` — side-by-side panes
- `YUIDimension.YD_VERT` — top/bottom panes

The initial split position is derived from the `weight()` values of the two children (first-child weight / total weight). Default is 50/50.

```python
paned = factory.createPaned(dlg, YUIDimension.YD_VERT)
left  = factory.createVBox(paned)
right = factory.createVBox(paned)
left.setWeight(YUIDimension.YD_VERT, 30)
right.setWeight(YUIDimension.YD_VERT, 70)
```

### 8.3 Alignment and size helpers

#### Alignment shortcuts

```python
factory.createLeft(parent)     # align child to left   (YAlignBegin  / YAlignUnchanged)
factory.createRight(parent)    # align child to right  (YAlignEnd    / YAlignUnchanged)
factory.createTop(parent)      # align child to top    (YAlignUnchanged / YAlignBegin)
factory.createBottom(parent)   # align child to bottom (YAlignUnchanged / YAlignEnd)
factory.createHCenter(parent)  # center child horizontally
factory.createVCenter(parent)  # center child vertically
factory.createHVCenter(parent) # center in both axes
```

Each returns a single-child container; add exactly one child widget to it.

#### Generic alignment

```python
factory.createAlignment(parent,
                         horAlignment: YAlignmentType,
                         vertAlignment: YAlignmentType) -> YWidget
```

For arbitrary combinations of `YAlignmentType` values.

#### Minimum size constraints

```python
factory.createMinWidth(parent, minWidth: int)  -> YWidget   # min width in pixels
factory.createMinHeight(parent, minHeight: int) -> YWidget  # min height in pixels
factory.createMinSize(parent, minWidth: int, minHeight: int) -> YWidget
```

These return single-child containers that impose a minimum size floor on their child. Internally they use an alignment widget with `setMinWidth/setMinHeight` applied.

### 8.4 Spacing and stretch

```python
factory.createSpacing(parent,
                       dim: YUIDimension,
                       stretchable: bool = False,
                       size_px: int = 0) -> YWidget
```

A blank spacer. When `stretchable=True` it expands to fill available space; when `False` it is a fixed gap of `size_px` pixels (pixel-to-character-cell conversion is applied on NCurses: 8 px/col horizontally, 16 px/row vertically).

Convenience variants:

```python
factory.createHStretch(parent)             # stretchable horizontal spacer
factory.createVStretch(parent)             # stretchable vertical spacer
factory.createHSpacing(parent, size_px=8)  # fixed horizontal gap (≈1 char)
factory.createVSpacing(parent, size_px=16) # fixed vertical gap (≈1 row)
```

### 8.5 Buttons

```python
factory.createPushButton(parent, label: str) -> YWidget
factory.createIconButton(parent, iconName: str, fallbackTextLabel: str) -> YWidget
```

`createIconButton` uses the icon on GUI backends; falls back to `fallbackTextLabel` on NCurses. Both support `setNotify()`, `setStretchable()` and `setFunctionKey()` from the base API.

### 8.6 Labels

```python
factory.createLabel(parent, text: str,
                     isHeading: bool = False,
                     isOutputField: bool = False) -> YWidget
factory.createHeading(parent, label: str) -> YWidget   # shortcut: isHeading=True
```

`isOutputField=True` styles the label as a read-only output field where supported.

### 8.7 Text input

```python
factory.createInputField(parent, label: str, password_mode: bool = False) -> YWidget
factory.createPasswordField(parent, label: str) -> YWidget   # alias: password_mode=True
factory.createMultiLineEdit(parent, label: str) -> YWidget
factory.createIntField(parent, label: str,
                        minVal: int, maxVal: int, initialVal: int) -> YWidget
```

`createPasswordField` is a convenience wrapper for `createInputField(..., password_mode=True)`.

Common methods on input widgets:

```python
w.value()           -> str | int    # current text / integer value
w.setValue(v)                       # set text / integer value
w.label()          -> str
w.setLabel(label: str)
```

### 8.8 CheckBox

```python
factory.createCheckBox(parent, label: str, is_checked: bool = False) -> YWidget
```

Value access:

```python
w.value()           -> YCheckBoxState   # YCheckBox_on / _off / _dont_care
w.setValue(state)                       # YCheckBoxState or bool
```

### 8.9 RadioButton

```python
factory.createRadioButton(parent, label: str = "", isChecked: bool = False) -> YWidget
```

Radio buttons within the same container are automatically grouped. Use `value()` / `setValue()` for state access.

### 8.10 ComboBox

```python
factory.createComboBox(parent, label: str, editable: bool = False) -> YWidget
```

- `editable=False` — drop-down list only.
- `editable=True` — allows free-text entry in addition to list selection.

Methods (inherited from `YSelectionWidget`):

```python
w.addItem(item: YItem | str)
w.addItems(items: list[YItem | str])
w.deleteAllItems()
w.selectedItem()   -> YItem | None
w.value()          -> str           # label of selected item
w.setValue(text: str)               # select by label
```

### 8.11 SelectionBox and MultiSelectionBox

```python
factory.createSelectionBox(parent, label: str) -> YWidget
factory.createMultiSelectionBox(parent, label: str) -> YWidget
```

`SelectionBox` allows one selection at a time; `MultiSelectionBox` allows zero or more. Both use the same `YSelectionWidget` API:

```python
w.addItem(item: YItem | str)
w.addItems(items: list[YItem | str])
w.deleteAllItems()
w.selectItem(item: YItem, selected: bool = True)
w.selectedItem()   -> YItem | None      # first selected (single / first in multi)
w.selectedItems()  -> list[YItem]       # all selected (multi)
w.hasSelectedItem() -> bool
w.itemsCount()     -> int
```

### 8.12 Tree

```python
factory.createTree(parent, label: str,
                    multiselection: bool = False,
                    recursiveselection: bool = False) -> YWidget
```

Items are `YTreeItem` objects (see §9.2). Use the same `YSelectionWidget` methods (`addItem`, `deleteAllItems`, `selectedItem`, etc.) to populate and query.

### 8.13 Table

```python
factory.createTable(parent, header: YTableHeader, multiSelection: bool = False) -> YWidget
```

`header` is a `YTableHeader` instance describing column titles and types (see §9.3). Rows are `YTableItem` objects (see §9.4).

Methods (from `YSelectionWidget`):

```python
w.addItem(row: YTableItem)
w.addItems(rows: list[YTableItem])
w.deleteAllItems()
w.selectedItem()  -> YTableItem | None
w.selectedItems() -> list[YTableItem]
```

### 8.14 RichText

```python
factory.createRichText(parent, text: str = "", plainTextMode: bool = False) -> YWidget
```

Renders HTML/rich text on GUI backends. `plainTextMode=True` disables markup interpretation.

```python
w.setValue(text: str)       # update content
w.value()     -> str
```

### 8.15 LogView

```python
factory.createLogView(parent, label: str, visibleLines: int, storedLines: int = 0) -> YWidget
```

A scrollable, append-only text log area. `storedLines` is a hint for the ring-buffer depth (0 = unlimited on most backends).

### 8.16 Frame

```python
factory.createFrame(parent, label: str = "") -> YWidget
factory.createCheckBoxFrame(parent, label: str = "", checked: bool = False) -> YWidget
```

`createFrame` is a single-child decorative container with a border and optional title. `createCheckBoxFrame` adds a checkbox that enables/disables its child.

### 8.17 ReplacePoint

```python
factory.createReplacePoint(parent) -> YWidget
```

A single-child placeholder whose content can be replaced at runtime by swapping the child widget.

### 8.18 DumbTab

```python
factory.createDumbTab(parent) -> YWidget
```

A tabbed container without a built-in stack; the application is responsible for showing/hiding child panes when tab events arrive.

### 8.19 MenuBar

```python
factory.createMenuBar(parent) -> YWidget
```

A menu bar. Populate it by adding `YMenuItem` objects (see §9.1). A `YMenuEvent` is delivered when the user selects an item.

### 8.20 ProgressBar

```python
factory.createProgressBar(parent, label: str, max_value: int = 100) -> YWidget
```

```python
w.setValue(value: int)    # current progress (0 … max_value)
w.value() -> int
```

### 8.21 Slider

```python
factory.createSlider(parent, label: str,
                      minVal: int, maxVal: int, initialVal: int) -> YWidget
```

```python
w.setValue(value: int)
w.value() -> int
```

### 8.22 Date / Time fields

```python
factory.createDateField(parent, label: str) -> YWidget
factory.createTimeField(parent, label: str) -> YWidget
```

Value is a string in ISO format (`"YYYY-MM-DD"` / `"HH:MM:SS"`).

```python
w.value()           -> str
w.setValue(text: str)
```

### 8.23 Image

```python
factory.createImage(parent, imageFileName: str) -> YWidget
```

Loads and displays an image file on GUI backends. NCurses renders an empty placeholder frame.

---

## 9. Model Classes

### 9.1 YItem

Used by selection widgets (ComboBox, SelectionBox, MultiSelectionBox).

```python
item = YItem(label: str, selected: bool = False, icon_name: str = "")

item.label()             -> str
item.setLabel(label: str)
item.selected()          -> bool
item.setSelected(selected: bool = True)
item.iconName()          -> str
item.setIconName(name: str)
item.hasIconName()       -> bool
item.index()             -> int
item.data()              -> any        # arbitrary application data
item.setData(data)
```

### 9.2 YMenuItem

Used with `createMenuBar()`. Items can be nested arbitrarily.

```python
menu = YMenuItem(label: str, icon_name: str = "",
                  enabled: bool = True,
                  is_menu: bool = False,
                  is_separator: bool = False)

menu.label()        -> str
menu.setLabel(label: str)
menu.iconName()     -> str
menu.setIconName(name: str)
menu.enabled()      -> bool
menu.setEnabled(on: bool = True)
menu.visible()      -> bool
menu.setVisible(on: bool = True)   # propagates to children
menu.isMenu()       -> bool
menu.isSeparator()  -> bool
menu.parentItem()   -> YMenuItem | None
menu.hasChildren()  -> bool

# Building the tree:
child_item = menu.addItem(label: str, icon_name: str = "")  -> YMenuItem
submenu    = menu.addMenu(label: str, icon_name: str = "")  -> YMenuItem
sep        = menu.addSeparator()                             -> YMenuItem
```

### 9.3 YTreeItem

Tree items for `createTree()`. `YTreeItem` extends `YItem` and can have child items.

```python
node = YTreeItem(label: str,
                  parent: YTreeItem = None,
                  selected: bool = False,
                  is_open: bool = False,
                  icon_name: str = "")

# Inherited from YItem:
node.label() / node.setLabel()
node.selected() / node.setSelected()
node.iconName() / node.setIconName() / node.hasIconName()
node.data() / node.setData()

# Tree-specific:
node.isOpen()           -> bool
node.parentItem()       -> YTreeItem | None
node.hasChildren()      -> bool
child = node.addChild(item: YTreeItem | str) -> YTreeItem
```

Nesting example:

```python
root = YTreeItem("Root", is_open=True)
child = root.addChild("Child")
grandchild = YTreeItem("Grandchild", parent=child)
tree_widget.addItem(root)
```

### 9.4 YTableHeader

Describes the column structure of a `createTable()` widget.

```python
header = YTableHeader()
header.addColumn(header: str,
                  checkBox: bool = False,
                  alignment: YAlignmentType = YAlignmentType.YAlignBegin)

header.columns()         -> int
header.hasColumn(col: int) -> bool
header.header(col: int)  -> str
header.isCheckboxColumn(col: int) -> bool
header.alignment(col: int) -> YAlignmentType
```

### 9.5 YTableCell

A single cell within a table row.

```python
cell = YTableCell(label: str = "",
                   icon_name: str = "",
                   sort_key: str = "",
                   parent: YTableItem = None,
                   column: int = -1,
                   checked: bool = None)  # None = not a checkbox column

cell.label()         -> str
cell.setLabel(label: str)
cell.iconName()      -> str
cell.setIconName(name: str)
cell.hasIconName()   -> bool
cell.sortKey()       -> str
cell.hasSortKey()    -> bool
cell.column()        -> int
cell.parent()        -> YTableItem | None
cell.itemIndex()     -> int    # row index in the table
cell.checked()       -> bool   # False when not a checkbox cell
cell.setChecked(val: bool = True)
```

### 9.6 YTableItem

A table row. Extends `YTreeItem` and holds a list of `YTableCell`.

```python
row = YTableItem(label: str = "")

# Convenience constructors:
row.addCell(cell_or_label, icon_name="", sort_key="")
row.addCells(*labels)    # e.g. row.addCells("Alice", "30", "Engineer")
row.deleteCells()

# Cell access:
row.cellCount()         -> int
row.hasCell(index: int) -> bool
row.cell(index: int)    -> YTableCell | None

# Convenience accessors (column 0 by default):
row.label(index: int = 0)    -> str
row.iconName(index: int = 0) -> str
row.checked(index: int = 0)  -> bool
```

---

## 10. Layout Reference

### Weight-based space distribution

Both `VBox` and `HBox` distribute extra space among their children proportionally to their weights on the relevant axis. Children with weight 0 receive space only as needed; children with non-zero weights share the remaining space.

```python
# 2/3 – 1/3 vertical split inside a VBox
top.setWeight(YUIDimension.YD_VERT, 2)
bot.setWeight(YUIDimension.YD_VERT, 1)
```

Absolute values are not significant — only ratios. `setWeight(dim, 67)` and `setWeight(dim, 33)` produce the same result as `setWeight(dim, 2)` and `setWeight(dim, 1)`.

### Paned split position

`createPaned` derives the initial split position from the first child's weight divided by the total weight of both children. If both children have weight 0 the divider starts at 50%. Weights also set the `QSplitter` stretch factors on Qt and the initial `Gtk.Paned` position on GTK.

### Stretchable vs. weight

`setStretchable(dim, True)` marks a widget as willing to expand; `setWeight` additionally controls the proportion. Use weights when siblings should share an unequal ratio; use stretchable for widgets that should simply fill remaining space equally.

```python
# three buttons; middle one gets twice as much horizontal space:
left.setStretchable(YUIDimension.YD_HORIZ, True)
mid.setWeight(YUIDimension.YD_HORIZ, 2)
right.setStretchable(YUIDimension.YD_HORIZ, True)
```

---

## 11. Complete Example

```python
import os
from manatools.aui.yui import (
    YUI, YUI_ui,
    YItem, YTreeItem, YTableHeader, YTableItem,
    YEventType, YEventReason, YUIDimension, YDialogColorMode,
)

ui = YUI_ui()
factory = ui.widgetFactory()

# Main dialog
dlg = factory.createMainDialog()
vbox = factory.createVBox(dlg)

# Combo
combo = factory.createComboBox(vbox, "Choose language:")
combo.addItems([YItem("Python", selected=True), YItem("Ruby"), YItem("Rust")])

# Splitter: tree on left, log on right
paned = factory.createPaned(vbox, YUIDimension.YD_HORIZ)
left  = factory.createVBox(paned)
right = factory.createVBox(paned)
left.setWeight(YUIDimension.YD_HORIZ, 40)
right.setWeight(YUIDimension.YD_HORIZ, 60)

tree = factory.createTree(left, "Packages:")
root = YTreeItem("base-system", is_open=True)
root.addChild("glibc")
root.addChild("bash")
tree.addItem(root)

log = factory.createLogView(right, "Output:", visibleLines=8)

# Buttons row
hbox = factory.createHBox(vbox)
factory.createHStretch(hbox)         # push buttons to the right
ok_btn     = factory.createPushButton(hbox, "OK")
cancel_btn = factory.createPushButton(hbox, "Cancel")

# Event loop
while True:
    ev = dlg.waitForEvent()
    if ev.eventType() == YEventType.CancelEvent:
        break
    if ev.eventType() == YEventType.WidgetEvent:
        if ev.widget() == cancel_btn:
            break
        if ev.widget() == ok_btn:
            sel = tree.selectedItem()
            print("Package:", sel.label() if sel else "(none)")
            print("Language:", combo.value())
            break

dlg.destroy()

# NCurses backend: restore terminal
if app.isTextMode():
    ui.shutdown()
```

---

## 12. Backend Differences Summary

| Feature | GTK | Qt | NCurses |
|---|---|---|---|
| Icons in widgets | Yes (GdkPixbuf) | Yes (QIcon) | Ignored |
| File dialogs | Gtk.FileDialog (GTK 4.10+) | QFileDialog | In-terminal overlay |
| `busyCursor()` | Best-effort | QApplication override cursor | No-op |
| `createPaned` divider | Gtk.Paned (idle-deferred) | QSplitter | Simulated in chars |
| `createImage` | Full image rendering | Full image rendering | Empty placeholder |
| `createRichText` | HTML via WebKit / Gtk.Label | QTextBrowser | Plain text fallback |
| Scrollbar auto-scroll | Supported | Supported | Limited |
| `shutdown()` required | No | No | Yes |

All `createXxx()` methods are implemented across all three backends unless noted above.

---

---

## 14. manatools.ui — High-level UI Helpers

`manatools.ui` provides ready-made helpers and base classes that sit on top of the AUI factory API. They handle the dialog lifecycle, event loop and title-bar save/restore automatically, so callers only need to supply a small `info` dictionary.

### 14.1 Import

```python
from manatools.ui import common
from manatools.ui.basedialog import BaseDialog, DialogType
from manatools.ui.helpdialog import HelpDialog
```

### 14.2 Message-box helpers (`manatools.ui.common`)

All helpers accept an `info` dictionary with the following keys. Keys marked *optional* may be omitted.

| Key | Type | Description |
|---|---|---|
| `title` | `str` | Window/title-bar label (optional) |
| `text` | `str` | Message body |
| `richtext` | `bool` | Render `text` as HTML/rich markup (default `False`) |
| `default_button` | `int` | Preselect button: `1` = affirmative, other = negative (optional) |
| `size` | `dict` \| `list/tuple` | Minimum size hint – see below |

#### Size hint

```python
# Dict form (pixels):
{'width': 480, 'height': 160}
# Legacy aliases accepted: 'column'/'columns', 'lines'/'rows'

# List / tuple form:
[480, 160]   # [width, height]
```

#### `destroyUI()`

```python
common.destroyUI()
```

No-op stub kept for API compatibility with legacy code. AUI handles backend lifecycle internally.

#### `msgBox(info)` → `int`

Plain message dialog with a single **Ok** button.

```python
common.msgBox({'title': 'Done', 'text': 'Operation completed.'})
```

Returns `1` always; `0` if `info` is falsy.

#### `infoMsgBox(info)` → `int`

Same as `msgBox` but displays a standard *information* icon next to the text.

#### `warningMsgBox(info)` → `int`

Same as `msgBox` but displays a standard *warning* icon.

#### `askOkCancel(info)` → `bool`

Dialog with **Ok** and **Cancel** buttons.

```python
confirmed = common.askOkCancel({
    'title': 'Confirm',
    'text': 'Delete selected items?',
    'default_button': 1,   # Ok is the default
})
```

Returns `True` (Ok pressed) or `False` (Cancel / window close).

#### `askYesOrNo(info)` → `bool`

Same as `askOkCancel` but labels the buttons **Yes** and **No**.

Returns `True` (Yes) or `False` (No / window close).

#### `AboutDialog(info=None, *, dialog_mode=AboutDialogMode.CLASSIC, size=None)`

Displays application metadata in classic or tabbed layout.

```python
from manatools.ui.common import AboutDialog, AboutDialogMode

AboutDialog(
    dialog_mode=AboutDialogMode.TABBED,
    size={'width': 480, 'height': 320},
)
```

Metadata (name, version, authors, description, license, credits, information, logo) is read from `YUI.app()` application attributes set earlier. The deprecated `info` dict overrides individual fields but emits a `DeprecationWarning`.

`AboutDialogMode`:

```python
class AboutDialogMode(Enum):
    CLASSIC = 1   # inline rich-text sections with Info / Credits buttons
    TABBED  = 2   # sections presented as DumbTab pages
```

### 14.3 `BaseDialog` (`manatools.ui.basedialog`)

`BaseDialog` is the base class for full application dialogs with an event manager.

```python
class BaseDialog:
    def __init__(self, title: str,
                 icon: str = "",
                 dialogType: DialogType = DialogType.MAIN,
                 minWidth: int = -1,
                 minHeight: int = -1): ...
```

Subclasses must override:

```python
def UIlayout(self, layout):
    """Build the dialog widget tree. `layout` is a VBox inside the dialog."""
    raise NotImplementedError
```

Optional override:

```python
def doSomethingIntoLoop(self):
    """Called once per event-loop iteration after events are dispatched."""
    pass
```

#### Key properties

```python
dialog.running  -> bool     # True while the event loop is active
dialog.timeout  -> int      # waitForEvent timeout in ms (0 = infinite)
dialog.factory  -> YWidgetFactory
dialog.eventManager -> EventManager
```

#### Running and stopping

```python
d = MyDialog()
d.run()          # blocks until ExitLoop() is called or dialog is closed

# inside any event handler:
self.ExitLoop()  # requests the loop to stop after the current iteration
```

#### `EventManager` (`manatools.eventmanager`)

Dispatches YUI events to registered Python callbacks. Obtained via `dialog.eventManager`.

```python
em = dialog.eventManager

# Widget events
em.addWidgetEvent(widget, callback)
em.addWidgetEvent(widget, callback, sendWidget=True)  # callback(widget, event)
em.removeWidgetEvent(widget, callback)

# Menu events
em.addMenuEvent(menuItem, callback)          # menuItem=None catches all
em.addMenuEvent(menuItem, callback, sendMenuItem=True)
em.removeMenuEvent(menuItem, callback)

# Timeout events
em.addTimeOutEvent(callback)
em.removeTimeOutEvent(callback)

# Cancel events
em.addCancelEvent(callback)
em.removeCancelEvent(callback)
```

Callback signatures:

```python
# Default (sendWidget/sendMenuItem = False):
def on_button():  ...

# With widget/item forwarding:
def on_button(widget, event): ...
```

#### Minimal `BaseDialog` example

```python
from manatools.ui import basedialog

class MyDialog(basedialog.BaseDialog):
    def __init__(self):
        super().__init__("My dialog", minWidth=400, minHeight=200)

    def UIlayout(self, layout):
        vbox = self.factory.createVBox(layout)
        self.label = self.factory.createLabel(vbox, "Hello, world!")
        btn = self.factory.createPushButton(vbox, "&Close")
        self.eventManager.addWidgetEvent(btn, self.on_close)

    def on_close(self):
        self.ExitLoop()

MyDialog().run()
```

### 14.4 `HelpDialog` (`manatools.ui.helpdialog`)

A popup rich-text help browser based on `BaseDialog`.

```python
from manatools.ui.helpdialog import HelpDialog
from manatools.basehelpinfo import HelpInfoBase

class MyHelp(HelpInfoBase):
    def home(self):
        return "<h2>Help</h2><p>Welcome to MyApp help.</p>"

    def show(self, url):
        # return HTML for internal links; None to open externally
        return None

HelpDialog(MyHelp(), title="Help", minWidth=500, minHeight=350).run()
```

- Internal links in rich text trigger `HelpInfoBase.show(url)`; if it returns a non-empty string the view is updated in place.
- External URLs (where `show()` returns `None`/empty) are opened via `webbrowser.open()`.
- `_normalize_dimension(value)` is a static helper that returns a positive int or 0 for invalid values.

### 14.5 Common pitfalls

- **`old_title` / `backupIcon` initialization** — all helpers initialize these variables to `None` before the `try` block so the `finally` clause never raises `UnboundLocalError` if dialog creation fails early.
- **Single `destroy()` path** — dialogs are destroyed exclusively in the `finally` block; do not call `dlg.destroy()` elsewhere in the same function to avoid double-free.
- **`DialogType.MAIN` vs `DialogType.POPUP`** — `MAIN` creates a `YMainDialog`; `POPUP` creates a `YPopupDialog` and stacks on top of the current topmost dialog. Most helpers use `POPUP`.

---

## 15. License and Contribution

This document is part of the `python-manatools` project (LGPLv2+). Update both code docstrings and this file when the API changes.
