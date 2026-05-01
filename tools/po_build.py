# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
"""
Translation build helper — compiles .po files to .mo binary files.

Usage (standalone)
------------------
    python3 tools/po_build.py
        Compile all languages to the default output tree:
        <project-root>/share/locale/<lang>/LC_MESSAGES/python-manatools.mo

    python3 tools/po_build.py <destdir>
        Compile all languages to <destdir>/<lang>/LC_MESSAGES/python-manatools.mo

        Useful for RPM packaging::

            python3 tools/po_build.py %{buildroot}%{_datadir}/locale
            # then in .spec: %find_lang python-manatools

The default output (``share/locale/`` in the project root) is also the
directory that ``pip wheel .`` picks up via the ``include`` directive in
``pyproject.toml``, so running this script before ``pip wheel`` bundles the
translations inside the wheel for pip/virtualenv users.

Packagers (RPM/DEB) who want .mo files installed in a custom location should
pass <destdir> explicitly.  ``tools/po-compile.sh`` offers the same feature
from the shell.
"""

import shutil
import subprocess
import sys
from pathlib import Path


_DOMAIN = "python-manatools"

# The script lives in <project-root>/tools/ → go one level up to reach project root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _compile_po_files(target_dir: Path) -> None:
    """Compile all po/*.po files to <target_dir>/<lang>/LC_MESSAGES/<domain>.mo."""
    po_dir = _PROJECT_ROOT / "po"

    if not po_dir.is_dir():
        print(f"po_build.py: no po/ directory found at {po_dir}, skipping")
        return

    msgfmt_bin = shutil.which("msgfmt")
    if not msgfmt_bin:
        print("po_build.py: WARNING: msgfmt not found — skipping translation compilation.")
        print("          Install gettext-tools and re-run:  python3 tools/po_build.py")
        return

    compiled = errors = 0
    for po_file in sorted(po_dir.glob("*.po")):
        lang = po_file.stem
        mo_dir = target_dir / lang / "LC_MESSAGES"
        mo_file = mo_dir / f"{_DOMAIN}.mo"
        mo_dir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                [msgfmt_bin, "--check", "--output-file", str(mo_file), str(po_file)],
                check=True,
                capture_output=True,
            )
            compiled += 1
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode(errors="replace").strip()
            print(f"po_build.py: WARNING: could not compile {po_file.name}: {stderr}")
            errors += 1

    print(
        f"po_build.py: compiled {compiled} translation file(s)"
        + (f", {errors} error(s)" if errors else "")
    )


def _validate_destdir(path_str: str) -> Path:
    """Validate and return a Path for <destdir>; raise SystemExit on bad input."""
    # Reject null bytes (security: would silently truncate the path on most OS).
    if "\x00" in path_str:
        print("po_build.py: error: destdir contains null bytes", file=sys.stderr)
        sys.exit(1)
    # Reject strings starting with '-' to avoid confusion with future options.
    if path_str.startswith("-"):
        print(
            f"po_build.py: error: destdir must not start with '-': {path_str!r}",
            file=sys.stderr,
        )
        sys.exit(1)
    # Reject empty string.
    if not path_str.strip():
        print("po_build.py: error: destdir must not be empty", file=sys.stderr)
        sys.exit(1)
    return Path(path_str)


if __name__ == "__main__":
    if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help")):
        print(
            f"Usage: python3 {sys.argv[0]} [<destdir>]\n"
            "\n"
            "  <destdir>  Optional output base directory for .mo files.\n"
            "             .mo files go to <destdir>/<lang>/LC_MESSAGES/python-manatools.mo\n"
            "             Default: share/locale/ relative to the project root.\n"
            "\n"
            "Example for RPM packaging:\n"
            "  python3 tools/po_build.py %{buildroot}%{_datadir}/locale\n"
            "  # then in .spec: %find_lang python-manatools"
        )
        sys.exit(0 if "--help" in sys.argv or "-h" in sys.argv else 1)

    if len(sys.argv) == 2:
        target_dir = _validate_destdir(sys.argv[1])
    else:
        # Default: compile into share/locale/ in the project root.
        # This is what pip wheel picks up via the include directive in pyproject.toml.
        target_dir = _PROJECT_ROOT / "share" / "locale"

    _compile_po_files(target_dir)
