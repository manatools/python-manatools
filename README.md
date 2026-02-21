# python-manatools #

![logo](https://avatars3.githubusercontent.com/u/19332721?v=3&s=200 "Python ManaTools")

Python ManaTools builds on the original Perl-based ManaTools idea, keeping the same goal of a shared toolkit and consistent UX while moving to Python to match systemd and D-Bus APIs. We are grateful to libyui for the foundation it provided, but this project now ships its own AUI layer and keeps evolving independently. Today it focuses on a backend-agnostic UI abstraction for GTK, Qt, and ncurses, plus the services and helpers needed by ManaTools.

See the AUI API documentation for details: [manatools AUI API](docs/manatools_aui_api.md).

## REQUIREMENTS

### Python
* Python 3

### D-Bus
* dbus-python

### UI backends (at least one)
* GTK4: PyGObject (`gi`)
* Qt6: PySide6
* ncurses: Python curses module (usually in the stdlib)

## INSTALLATION
python setup.py install
