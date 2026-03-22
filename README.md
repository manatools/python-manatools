# python-manatools #

![logo](https://avatars3.githubusercontent.com/u/19332721?v=3&s=200 "Python ManaTools")

Python ManaTools builds on the original Perl-based ManaTools idea, keeping the same goal of a shared toolkit and consistent UX while moving to Python to match systemd and D-Bus APIs. We are grateful to libyui for the foundation it provided, but this project now ships its own AUI layer and keeps evolving independently. Today it focuses on a backend-agnostic UI abstraction for GTK, Qt, and ncurses, plus the services and helpers needed by ManaTools.

See the AUI API documentation for details: [manatools AUI API](docs/manatools_aui_api.md).

## REQUIREMENTS

### Python >= 3.6

### Core dependencies (always required)
* **dbus-python** — D-Bus bindings used by `manatools.services`
* **PyYAML** — YAML configuration file support (`manatools.config`)
* **python-gettext** — internationalisation helpers

### UI backends (at least one required)

#### GTK 4 backend
* **PyGObject >= 3.42** (`gi`) — Python GObject introspection bindings
* **GTK 4** — the GTK 4 toolkit libraries (`gtk4`)
* **GdkPixbuf 2** — image loading for icons (`gdk-pixbuf2`)
* **pycairo** — Cairo drawing context used by GTK widgets (`python3-cairo`)

#### Qt backend
* **PySide6 >= 6.5.0** — Qt 6 Python bindings

#### ncurses backend
* **curses** — included in the Python standard library (no extra install needed)

## INSTALLATION

```
pip install python-manatools
```

Or from sources:

```
python setup.py install
```

