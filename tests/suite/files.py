import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Final, Iterator

import pytest

OPEN_FOLDER: Final[int] = 0o755
LOCKED_FOLDER: Final[int] = 0o000
NAMES_ONLY_FOLDER: Final[int] = 0o444
FOLDER_PERMISSIONS_HOLD: Final[bool] = sys.platform != "win32" and os.geteuid() != 0

requires_folder_permissions = pytest.mark.skipif(
    not FOLDER_PERMISSIONS_HOLD,
    reason="a folder's permissions lock it on a POSIX system for a reader other than root",
)


def empty_file(directory: Path, name: str) -> Path:
    """Writes an empty file called ``name`` under ``directory``, which a check that reads only names and presence accepts."""
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


@contextmanager
def held_at(folder: Path, mode: int) -> Iterator[Path]:
    """Holds ``folder`` at the permissions ``mode`` while the block runs, and opens it again after.

    The folder opens again however the block ends, so the case's temporary tree can be cleared.
    """
    folder.chmod(mode)
    try:
        yield folder
    finally:
        folder.chmod(OPEN_FOLDER)
