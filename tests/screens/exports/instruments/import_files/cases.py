from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, Tuple

READ_FAILED: Final[str] = "Failed to read an instrument from"
NO_FILE: Final[str] = "No instrument file at"
FOREIGN_BYTES: Final[bytes] = b"These bytes were written by another program and hold no instrument.\n"
HALF: Final[int] = 2


@dataclass(frozen=True)
class BrokenFile:
    """A file the import meets broken: how it is laid in the home and what the application logs.

    Attributes:
        lay: Writes the broken file at the first path, given the path of a whole exported file.
        logged: The start of the error the application logs for this file.
        not_found: Whether the application answers with its file-not-found message.
    """

    name: str
    lay: Callable[[Path, Path], None]
    logged: str
    not_found: bool


def foreign(destination: Path, _exported: Path) -> None:
    """Writes bytes of another program in place of an instrument."""
    destination.write_bytes(FOREIGN_BYTES)


def truncated(destination: Path, exported: Path) -> None:
    """Writes the first half of the exported file."""
    content = exported.read_bytes()
    destination.write_bytes(content[: len(content) // HALF])


def missing(_destination: Path, _exported: Path) -> None:
    """Leaves the file absent, so the import finds it gone."""


BROKEN_FILES: Final[Tuple[BrokenFile, ...]] = (
    BrokenFile(name="Foreign", lay=foreign, logged=READ_FAILED, not_found=False),
    BrokenFile(name="Truncated", lay=truncated, logged=READ_FAILED, not_found=False),
    BrokenFile(name="Missing", lay=missing, logged=NO_FILE, not_found=True),
)
