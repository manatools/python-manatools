# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
"""
Shared helpers for the manatools.ui package.
"""

import gettext
import importlib.resources
import os
from pathlib import Path

_DOMAIN = "python-manatools"


def _get_translation() -> gettext.NullTranslations:
    """Return a GNUTranslations (or NullTranslations fallback) for python-manatools.

    .mo binary files are compiled from .po sources by build.py (pip/wheel path)
    or tools/po-compile.sh (packager/distro path).  They are never committed to
    the repository.

    Search order:

    1. ``MANATOOLS_LOCALE_DIR`` environment variable — developer / CI override.
    2. ``$XDG_DATA_HOME/locale/`` (default ``~/.local/share/locale/``) — per XDG
       Base Directory spec, user-scoped locale data lives here.  Useful when a
       user manually installs translations or when a future install-locale command
       places them here.
    3. ``manatools/locale/`` inside the installed package — legacy path, kept for
       backwards compatibility with older wheels that bundled .mo there.
       Found via ``importlib.resources``.
    4. ``share/locale/`` relative to ``__file__`` — primary path for pip/wheel
       installs with the current build layout.  ``po_build.py`` (the Poetry build
       hook) compiles .po → ``share/locale/``; pip installs that tree next to
       ``manatools/`` in site-packages so the relative path resolves correctly.
       Also works in a source checkout after running ``python3 po_build.py`` or
       ``tools/po-compile.sh``.
    5. ``/usr/share/locale/`` — distro package installs (RPM, DEB, …).
    6. ``NullTranslations`` — no translation found; strings pass through in English.
    """
    search_dirs: list[str] = []

    # 1. Developer / CI override
    env_dir = os.environ.get("MANATOOLS_LOCALE_DIR")
    if env_dir:
        search_dirs.append(env_dir)

    # 2. XDG user locale: $XDG_DATA_HOME/locale/ (default ~/.local/share/locale/)
    xdg_data_home = os.environ.get("XDG_DATA_HOME") or str(
        Path.home() / ".local" / "share"
    )
    xdg_locale = Path(xdg_data_home) / "locale"
    if xdg_locale.is_dir():
        search_dirs.append(str(xdg_locale))

    # 3. Package-bundled locale (populated by build.py / Poetry build hook).
    #    Works for regular pip installs and editable installs after running build.py.
    try:
        pkg_locale = importlib.resources.files("manatools").joinpath("locale")
        pkg_path = Path(str(pkg_locale))
        if pkg_path.is_dir():
            search_dirs.append(str(pkg_path))
    except Exception:
        pass

    # 4. Source-tree share/locale/ — produced by tools/po-compile.sh for packagers.
    #    __file__ is manatools/ui/__init__.py; go up 3 levels to project root.
    try:
        src_locale = Path(__file__).parent.parent.parent / "share" / "locale"
        if src_locale.is_dir():
            search_dirs.append(str(src_locale))
    except Exception:
        pass

    # 5. System locale (distro packages)
    search_dirs.append("/usr/share/locale")

    for locale_dir in search_dirs:
        try:
            return gettext.translation(_DOMAIN, localedir=locale_dir, fallback=False)
        except FileNotFoundError:
            continue

    return gettext.NullTranslations()

