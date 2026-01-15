"""
manatools.aui.backends package initializer.

Provides a small, lazy-loading shim so callers can import submodules
(e.g. 'from manatools.aui.backends.gtk import ...') while keeping the
package import lightweight and well-logged.
"""
import importlib
import logging
from types import ModuleType

_logger = logging.getLogger("manatools.aui.backends")

# advertised subpackages (may be absent if not installed)
__all__ = ["gtk", "qt", "ncurses"]

def __getattr__(name: str) -> ModuleType:
    """
    Lazy-import backend submodules on attribute access (PEP 562).
    Raises AttributeError if submodule cannot be imported.
    """
    if name in __all__:
        full = f"{__name__}.{name}"
        try:
            mod = importlib.import_module(full)
            globals()[name] = mod
            return mod
        except Exception:
            _logger.debug("Failed to import backend submodule %s", full, exc_info=True)
            # re-raise as AttributeError to match import semantics
            raise AttributeError(f"cannot import name {name!r} from {__name__}") from None
    raise AttributeError(f"module {__name__} has no attribute {name!r}")

def __dir__():
    # expose advertised backends plus any already imported names
    return sorted(list(__all__) + [k for k in globals().keys() if not k.startswith("_")])
