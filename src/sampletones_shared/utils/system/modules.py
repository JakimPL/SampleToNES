import importlib.util
from typing import Final

JEEPNEY_MODULE: Final[str] = "jeepney"
TKINTER_MODULE: Final[str] = "tkinter"


def module_available(module: str) -> bool:
    """Whether this interpreter imports a module, which is how an optional dependency is reached.

    A dependency declared for one platform, or shipped as a separate system package, is present on
    some machines and absent on others. Probing the name keeps the import inside the branch that
    needs it, so startup stands on what the machine actually carries.

    Args:
        module: The module's importable name.

    Returns:
        bool: ``True`` where this interpreter finds the module installed.
    """
    return importlib.util.find_spec(module) is not None
