# ManaTools Web Backend

A web-based backend for python-manatools AUI that renders applications in a web browser via HTTP/WebSocket.

## Overview

This package adds a new `web` backend to python-manatools, allowing any ManaTools application to be accessed through a web browser without any code changes.

## Usage

### Running with Web Backend

Set the `YUI_BACKEND` environment variable to `web`:

```bash
# Linux/macOS
export YUI_BACKEND=web
python your_app.py

# Windows (Command Prompt)
set YUI_BACKEND=web
python your_app.py

# Windows (PowerShell)
$env:YUI_BACKEND="web"
python your_app.py
```

When the application starts, it will display a URL:

```
==================================================
  Dialog available at: http://127.0.0.1:8080/
  Open this URL in your web browser
==================================================
```

Open this URL in any modern web browser to interact with the application.

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

The web server binds to `127.0.0.1` (localhost only) by default. To allow remote access, modify `server.py`:

```python
self._server = WebServer(self, host="0.0.0.0", port=8080)
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
