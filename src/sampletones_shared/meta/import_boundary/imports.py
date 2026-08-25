import re
from typing import Final, Optional

from sampletones_shared.meta.source.modules import MODULE_SEPARATOR

IMPORT_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\s*(import|from)\s+([\w.]+)")


def imported_module(line: str) -> Optional[str]:
    """The dotted module one line of source imports.

    Args:
        line: Line to read.

    Returns:
        Optional[str]: The module the line imports, or `None` where the line imports nothing.
    """
    match = IMPORT_PATTERN.match(line)
    return match.group(2) if match is not None else None


def matches_prefix(module: str, prefix: str) -> bool:
    """Whether a dotted module is the prefix itself or a module underneath it."""
    return module == prefix or module.startswith(prefix + MODULE_SEPARATOR)
