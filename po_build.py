# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
"""
Translation build helper — compiles .po files to .mo binary files for the wheel.

This script serves two purposes:

1. **Poetry build hook** (called automatically during ``pip install`` / ``poetry build``):
   The ``build(setup_kwargs)`` function is invoked by Poetry before assembling the
   wheel.  It compiles ``po/*.po`` → ``manatools/locale/<lang>/LC_MESSAGES/python-manatools.mo``
   so the compiled translations are bundled *inside* the wheel under the package
   tree.  After installation via pip, they are found at runtime by
   ``manatools.ui._get_translation()`` using ``importlib.resources``.

2. **Standalone developer tool** (``python3 build.py``):
   Run manually after a ``git clone`` to populate ``manatools/locale/`` before
   doing ``pip install -e .`` (editable install).

Packagers (RPM/DEB) should use ``tools/po-compile.sh`` which writes to
``share/locale/`` and can be installed to ``/usr/share/locale/``.  The system
path is also covered by ``_get_translation()`` (lookup #5).

Note on setuptools-gettext alternative:
  The same result can be achieved with the ``setuptools-gettext`` plugin by
  switching the build backend to ``setuptools``.  See sow/TODO-LOCALIZATION for
  details.  For now we keep poetry-core as the build backend and use this hook.
"""

import shutil
import subprocess
from pathlib import Path


_DOMAIN = "python-manatools"


def _compile_po_files(target_dir: Path="share") -> None:
    """Compile all po/*.po files to <target_dir>/<lang>/LC_MESSAGES/<domain>.mo."""
    root = Path(__file__).parent
    po_dir = root / "po"

    if not po_dir.is_dir():
        print("build.py: no po/ directory found, skipping translation compilation")
        return

    msgfmt_bin = shutil.which("msgfmt")
    if not msgfmt_bin:
        print("build.py: WARNING: msgfmt not found — skipping translation compilation.")
        print("          Install gettext-tools and re-run:  python3 build.py")
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
            print(f"build.py: WARNING: could not compile {po_file.name}: {stderr}")
            errors += 1

    print(f"build.py: compiled {compiled} translation file(s)"
          + (f", {errors} error(s)" if errors else ""))


def build(setup_kwargs: dict) -> None:
    """Poetry PEP-517 build hook — compiles .mo into manatools/locale/ for the wheel."""
    root = Path(__file__).parent
    _compile_po_files(root / "share" / "locale")


if __name__ == "__main__":
    # Standalone: compile into manatools/locale/ (editable install / development).
    # For the packager target (share/locale/) use tools/po-compile.sh instead.
    root = Path(__file__).parent
    _compile_po_files(root / "share" / "locale")
