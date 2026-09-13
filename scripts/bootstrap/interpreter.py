import sys
from typing import Final, Tuple

REQUIRED_VERSION: Final[Tuple[int, int]] = (3, 12)
DOWNLOADS: Final[str] = "https://www.python.org/downloads/"


def require_python(version: Tuple[int, int]) -> None:
    """Holds the interpreter running the script to ``version`` or newer.

    Importing ``bootstrap`` runs it first, so an older interpreter is told the version it needs
    before a script reaches the standard library that version brings.

    Args:
        version: The oldest major and minor version the scripts run on.

    Raises:
        SystemExit: If the interpreter is older, naming where a newer one is downloaded.
    """
    if tuple(sys.version_info[:2]) >= version:
        return

    major, minor = version
    raise SystemExit(
        f"ERROR: Python {major}.{minor} or newer is required.\n"
        f"Please install Python {major}.{minor}+ from {DOWNLOADS}"
    )


def running_version() -> str:
    """The version of the interpreter running the script, as ``major.minor.micro``."""
    return ".".join(str(part) for part in sys.version_info[:3])
