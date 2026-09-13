import sys
from typing import Final, Tuple

REQUIRED_VERSION: Final[Tuple[int, int]] = (3, 12)
DOWNLOADS: Final[str] = "https://www.python.org/downloads/"


def require_python(version: Tuple[int, int]) -> None:
    """Holds the interpreter running the script to ``version`` or newer.

    Args:
        version: The oldest major and minor version the operation runs on.

    Raises:
        SystemExit: If the interpreter is older, naming where a newer one is downloaded.
    """
    running = sys.version_info
    if (running.major, running.minor) >= version:
        print(f"Detected Python version: {running.major}.{running.minor}.{running.micro}")
        return

    major, minor = version
    raise SystemExit(
        f"ERROR: Python {major}.{minor} or newer is required.\n"
        f"Please install Python {major}.{minor}+ from {DOWNLOADS}"
    )
