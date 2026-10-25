# ManaTools Web Backend

A web-based backend for python-manatools AUI that renders applications in a web browser via HTTP/WebSocket.

## Overview

This package adds a new `web` backend to python-manatools, allowing any ManaTools application to be accessed through a web browser without any code changes.

## Usage

### Running with Web Backend

Set the `MUI_BACKEND` environment variable to `web`:

```bash
# Linux/macOS
export MUI_BACKEND=web
python your_app.py

# Windows (Command Prompt)
set MUI_BACKEND=web
python your_app.py

# Windows (PowerShell)
$env:MUI_BACKEND="web"
python your_app.py
```

When the application opens its first dialog, it will display a URL:

```
==================================================
  Dialog available at: http://127.0.0.1:43807/
  Open this URL in your web browser
==================================================
```

Open this URL in any modern web browser to interact with the application.
The port is picked by the system unless `MUI_WEB_PORT` is set (see
[Configuration](#configuration)).

The process runs a single server: every dialog, main or popup, is served on
the same URL.  A popup is shown as a modal over the page, and when a main
dialog opens or closes the browser reloads onto the new top dialog by itself.
Between dialogs the page waits; it is told the application has closed only on
`YUI.ui().shutdown()` or interpreter exit.

### Application Code

No changes are needed to your application code! The same code works with Qt, GTK, curses, or web backend:

```python
from manatools.aui.yui import YUI

factory = YUI.widgetFactory()
dialog = factory.createMainDialog()
vbox = factory.createVBox(dialog)

factory.createLabel(vbox, "Hello, World!")
button = factory.createPushButton(vbox, "&OK")

dialog.open()

while True:
    event = dialog.waitForEvent()
    if event.widget() == button:
        break

dialog.destroy()
```

## Architecture

```
Browser (HTML/CSS/JS)
        │
        │ WebSocket / HTTP
        ▼
┌─────────────────────────────┐
│      WebServer (Python)      │
│   - HTTP: Serve HTML/CSS/JS  │
│   - WebSocket: Real-time     │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│      YDialogWeb              │
│   - Event queue              │
│   - Widget tree → HTML       │
│   - waitForEvent() blocks    │
└─────────────────────────────┘
```

## Widget Support

All standard ManaTools widgets are supported:

| Widget | Status | Notes |
|--------|--------|-------|
| YDialog | ✅ | Main and popup dialogs |
| YVBox, YHBox | ✅ | Layout containers |
| YLabel | ✅ | Text and headings |
| YPushButton | ✅ | With icons and shortcuts |
| YInputField | ✅ | Text and password mode |
| YCheckBox | ✅ | |
| YRadioButton | ✅ | |
| YComboBox | ✅ | Dropdown selection |
| YSelectionBox | ✅ | List selection |
| YFrame | ✅ | Grouped content |
| YCheckBoxFrame | ✅ | Toggleable frame |
| YProgressBar | ✅ | |
| YSlider | ✅ | |
| YTable | ✅ | |
| YTree | ✅ | |
| YRichText | ✅ | HTML content |
| YMenuBar | ✅ | |
| YImage | ✅ | |
| YIntField | ✅ | Number input |
| YDateField | ✅ | Date picker |
| YTimeField | ✅ | Time picker |
| YMultiLineEdit | ✅ | Textarea |
| YLogView | ✅ | Log display |
| YDumbTab | ✅ | Tab bar |
| YPaned | ✅ | Split panes |
| YSpacing | ✅ | Layout spacing |
| YAlignment | ✅ | Content alignment |
| YReplacePoint | ✅ | Dynamic content |

## File Structure

```
manatools/aui/
├── yui.py              # Modified: Added Backend.WEB
├── yui_web.py          # NEW: YUIWeb, YWidgetFactoryWeb, YApplicationWeb
└── backends/
    ├── __init__.py     # Modified: Added "web" to __all__
    └── web/            # NEW: All web backend files
        ├── __init__.py
        ├── commonweb.py
        ├── server.py
        ├── dialogweb.py
        ├── vboxweb.py
        ├── hboxweb.py
        ├── labelweb.py
        ├── pushbuttonweb.py
        ├── inputfieldweb.py
        ├── checkboxweb.py
        ├── comboboxweb.py
        ├── selectionboxweb.py
        ├── frameweb.py
        ├── progressbarweb.py
        ├── alignmentweb.py
        ├── spacingweb.py
        ├── treeweb.py
        ├── tableweb.py
        ├── richtextweb.py
        ├── menubarweb.py
        ├── replacepointweb.py
        ├── checkboxframeweb.py
        ├── radiobuttonweb.py
        ├── intfieldweb.py
        ├── multilineditweb.py
        ├── imageweb.py
        ├── dumbtabweb.py
        ├── sliderweb.py
        ├── datefieldweb.py
        ├── timefieldweb.py
        ├── logviewweb.py
        ├── panedweb.py
        └── static/
            ├── css/
            │   └── manatools.css
            └── js/
                └── manatools.js
```

## Browser Support

- Chrome/Chromium (recommended)
- Firefox
- Safari
- Edge

WebSocket is required for real-time updates. Falls back to HTTP POST for older browsers.

## Configuration

The web server binds to `127.0.0.1` (localhost only).  Its port is the one
in the `MUI_WEB_PORT` environment variable, or a free port picked by the
system when the variable is unset or `0`.  A fixed port keeps the URL the same
across restarts, so a bookmarked tab can simply be reloaded; if the port is
taken, the server falls back to a free one and logs a warning.

```bash
MUI_BACKEND=web MUI_WEB_PORT=8080 python your_app.py
```

To allow remote access, change the host `get_server()` passes in `server.py`:

```python
server = WebServer(host="0.0.0.0")
```

⚠️ **Security Warning**: Allowing remote access exposes your application to the network. Consider adding authentication for production use.

## Dependencies

**None!** The web backend uses only Python standard library:
- `http.server` - HTTP serving
- `threading` - Background server
- `queue` - Event queue
- `json` - WebSocket messages
- `hashlib`, `base64`, `struct` - WebSocket protocol

## Limitations

- File dialogs (`askForExistingFile`, etc.) are not supported in the browser
- Window positioning/sizing is handled by the browser
- System tray integration is not available
- Native menus use HTML menus instead

## License

LGPLv2+ (same as python-manatools)

## Author

Matteo Pasotti <xquiet@coriolite.com>

Based on python-manatools by Angelo Naselli <anaselli@linux.it>
