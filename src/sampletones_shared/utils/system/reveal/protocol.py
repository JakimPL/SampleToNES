from pathlib import Path
from typing import Protocol, Tuple


class RevealBackend(Protocol):
    """The file-revealing surface that callers depend on.

    Every implementation opens the desktop's file manager on the given files, so callers
    reveal a set of paths through this type and stay independent of the environment that
    draws the windows.
    """

    def open(self, paths: Tuple[Path, ...]) -> None: ...
