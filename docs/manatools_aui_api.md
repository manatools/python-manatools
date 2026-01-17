# manatools AUI - Application API (YUI.application)

Overview
--------
The object returned by `YUI.app()` / `YUI.application()` / `YUI.yApp()` is the backend-specific Application object (Qt, GTK, or NCurses). Obtain it via:

```python
from manatools.aui.yui import YUI
app = YUI.app()          # backend-specific application object
# aliases: YUI.application(), YUI.yApp()
```

This document lists the common methods that application code should use in a backend-agnostic way and highlights differences and missing documentation.

Common public methods (backend-agnostic)
---------------------------------------
These methods are implemented by backend application classes (Qt, GTK, NCurses). Signatures below are the expected API the application code should rely on.

- setApplicationTitle(title: str)
  - Set the application title. Backends attempt to propagate it to windows/dialogs (Qt: QApplication; GTK: active windows; NCurses: terminal window title escape codes).

- applicationTitle() -> str
  - Return current application title.

- setApplicationIcon(icon_spec: str)
  - Set application icon specification (theme name or file path). Backends attempt to resolve and apply the icon where possible. Behavior varies by backend.

- applicationIcon() -> str
  - Return the currently configured icon specification.

- setIconBasePath(path: str) / iconBasePath()
  - Provide a base path used when resolving icon file names prior to theme lookup.

- setProductName(name: str) / productName() -> str
  - Set/read product name metadata used by dialogs or platform integration.

- setApplicationName(name: str) / applicationName() -> str
- setVersion(version: str) / version() -> str
- setAuthors(authors: str) / authors() -> str
- setDescription(desc: str) / description() -> str
- setLicense(text: str) / license() -> str
- setCredits(credits: str) / credits() -> str
- setInformation(info: str) / information() -> str
- setLogo(path: str) / logo() -> str
  - About dialog and metadata setters/getters.

- isTextMode() -> bool
  - Returns True for text-mode (NCurses) backend. Use to adapt UI or behavior.

- busyCursor() / normalCursor()
  - Show/hide busy cursor. Implementations differ (Qt uses override cursor; GTK and NCurses may be no-op or best-effort).

File chooser helpers (common usage)
-----------------------------------
These functions present file/directory selection dialogs. Implementations differ across backends; calls should be treated as blocking helpers that return the selected path or an empty string when canceled.

- askForExistingDirectory(startDir: str, headline: str) -> str
- askForExistingFile(startWith: str, filter: str, headline: str) -> str
- askForSaveFileName(startWith: str, filter: str, headline: str) -> str

Notes:
- `filter` is typically a semicolon-separated list of patterns like `"*.txt;*.md"`.
- Qt uses QFileDialog (synchronous).
- GTK attempts Gtk.FileDialog (GTK4.10+) and supports portals/fallbacks.
- NCurses provides an in-UI browsing overlay; behavior and filter parsing are implemented in Python.

Practical examples
------------------
Set title and icon (backend-agnostic):

```python
app = YUI.app()
app.setApplicationTitle("MyApp")
app.setIconBasePath("/usr/share/myapp/icons")
app.setApplicationIcon("myapp-icon")   # theme name or absolute path
```

Open a file chooser:

```python
fn = app.askForExistingFile("/home/user", "*.iso;*.img", "Open image")
if fn:
    print("Selected:", fn)
```

## Factory createXXX methods

The widget factory (returned by `YUI.ui().widgetFactory()` / `YUI_ui().widgetFactory()`) provides unified constructors for UI widgets across backends. Use the factory to create dialogs, layout containers and widgets in a backend-agnostic way.

General pattern:
- Call `factory.createXxx(parent, ...)` to create widget X.
- The returned object is a YWidget subclass; call widget methods (setValue, setLabel, addItem, etc.) and use `dialog.waitForEvent()` loop to handle events.

Common factory methods (signatures and brief notes)

- createMainDialog(color_mode=YDialogColorMode.YDialogNormalColor)
  - Returns a main dialog (blocking UI container).
- createPopupDialog(color_mode=YDialogColorMode.YDialogNormalColor)
  - Returns a popup dialog.

Layout containers
- createVBox(parent)
- createHBox(parent)
  - Vertical / horizontal layout containers (parent is a dialog or another container).

Common leaf widgets
- createPushButton(parent, label)
  - Button widget. Use `setNotify()`, `setIcon()`, `setStretchable()`.
- createIconButton(parent, iconName, fallbackTextLabel)
  - Convenience: pushbutton with icon.
- createLabel(parent, text, isHeading=False, isOutputField=False)
- createHeading(parent, label)
  - Label / heading above controls.

Input and selection
- createInputField(parent, label, password_mode=False)
  - Single-line text input.
- createMultiLineEdit(parent, label)
- createIntField(parent, label, minVal, maxVal, initialVal)
- createCheckBox(parent, label, is_checked=False)
- createPasswordField(parent, label)
- createComboBox(parent, label, editable=False)
  - Combo/select widget. Supports addItem/addItems/deleteAllItems and icons where supported.
- createSelectionBox(parent, label)
- createMultiSelectionBox(parent, label)
  - Single- or multi-selection lists. Use `addItem`, `addItems`, `deleteAllItems`, `selectItem`, `selectedItems()`.

Progress/visual widgets
- createProgressBar(parent, label, max_value=100)
- createImage(parent, imageFileName)
  - Backends may support autoscale/stretch; icon/image loading depends on backend.
- createTree(parent, label, multiselection=False, recursiveselection=False)
- createTable(parent, header: YTableHeader, multiSelection=False)
- createRichText(parent, text="", plainTextMode=False)
- createLogView(parent, label, visibleLines, storedLines=0)

Grouping / frames / special widgets
- createFrame(parent, label="")
- createCheckBoxFrame(parent, label="", checked=False)
- createRadioButton(parent, label="", isChecked=False)
- createReplacePoint(parent)
- createDumbTab(parent)

Layout helpers
- createSpacing(parent, dim: YUIDimension, stretchable: bool = False, size_px: int = 0)
- createHStretch(parent), createVStretch(parent)
- createHSpacing(parent, size_px=8), createVSpacing(parent, size_px=16)

Misc
- createMenuBar(parent)
- createSlider(parent, label, minVal, maxVal, initialVal)
- createDateField(parent, label)
- createTimeField(parent, label)

Notes and backend differences
- All `createXXX` methods return backend-specific widget objects implementing the YWidget API. Call generic methods (setLabel, setValue, addItem, deleteAllItems, setStretchable, setWeight) on those objects.
- Not all backends support icons, autoscaling or the same filter semantics; the factory hides creation differences but some features are best-effort per backend.
- For selection widgets (ComboBox / SelectionBox / Tree / Table):
  - Use addItem/addItems/deleteAllItems at runtime to keep the widget and backend in sync.
  - Only one item should be selected in single-selection widgets; when selecting programmatically ensure previous selection is cleared (most backends handle this if you use widget.setValue or item.setSelected()).
  - Icons, if provided via YItem.iconName(), are displayed on GUI backends (GTK/Qt) when supported; ncurses ignores icons.

Minimal example
```python
# create a dialog with a combo and a button (backend-agnostic)
ui = YUI_ui()
factory = ui.widgetFactory()
dlg = factory.createMainDialog()
vbox = factory.createVBox(dlg)
combo = factory.createComboBox(vbox, "Choose:", editable=False)
combo.addItems([YItem("One"), YItem("Two", selected=True), YItem("Three")])
btn = factory.createPushButton(vbox, "OK")

# basic event loop
while True:
    ev = dlg.waitForEvent()
    if ev.eventType() == YEventType.CancelEvent:
        dlg.destroy()
        break
    if ev.eventType() == YEventType.WidgetEvent and ev.widget() == btn:
        print("Selected:", combo.value())
        dlg.destroy()
        break
```

Backend differences and caveats
-------------------------------
- Icon resolution: backends first try icon base path, then theme lookup. Icons may not be available or may be treated differently (GTK uses GdkPixbuf, Qt uses QIcon, NCurses ignores icons).
- File dialogs:
  - GTK uses Gtk.FileDialog on modern GTK4; availability depends on GTK version and platform (portal fallbacks exist).
  - NCurses dialog is implemented with an internal overlay; features (filters, navigation) differ from GUI backends.
- Cursor APIs and certain visual behaviors are backend-specific and may be no-op in text mode.
- Methods that interact with windows/views (e.g., applying an icon to open dialogs) perform best-effort updates and may silently fail if no dialog/window is available.


License and contribution
------------------------
This document is provided to help developers use the cross-backend Application API. Please update the code docstrings and this document when API changes occur.
