import os
import sys
import tempfile
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


def _symlinks_are_permitted() -> bool:
    """Reports whether this machine lets an unprivileged process create a symlink.

    Windows grants the privilege only under Developer Mode or elevation, so the probe
    creates one in a throwaway directory and reads the answer from the attempt.
    """
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        try:
            (root / "probe").symlink_to(root, target_is_directory=True)
        except OSError:
            return False

    return True


SYMLINKS_PERMITTED: Final[bool] = _symlinks_are_permitted()

requires_symlinks = pytest.mark.skipif(
    not SYMLINKS_PERMITTED,
    reason="creating a symlink requires a privilege this machine withholds",
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
