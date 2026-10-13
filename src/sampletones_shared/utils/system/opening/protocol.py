from pathlib import Path
from typing import Protocol


class FileOpener(Protocol):
    """The surface that shows a file in the program the system gives its kind.

    Callers hand a file over through this type, a page to the browser among them, and read alike
    on every system.
    """

    def open(self, path: Path) -> None:
        """Shows ``path`` in the program the system gives its kind.

        Raises:
            OSError: If no program takes the file.
        """
