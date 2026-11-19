import os
import shutil
from pathlib import Path

from sampletones_shared.types.path import Pathlike

from .paths import is_within, to_path


def remove_path(path: Pathlike) -> Path:
    """Removes a file-system path and returns the normalized target path.

    File paths are unlinked and directory paths are removed recursively. Symbolic
    links are unlinked as paths of their own, which keeps the operation scoped to
    the selected entry.
    """
    target = to_path(path)
    if target.is_symlink() or target.is_file():
        target.unlink()
        return target

    if target.is_dir():
        shutil.rmtree(target)
        return target

    raise FileNotFoundError(f"Path does not exist: {target}")


def removal_takes(removed: Path, path: Path) -> bool:
    """Whether :func:`remove_path` on ``removed`` takes ``path`` away with it.

    Every path spelled through ``removed`` goes with it. A link is removed as a path of its own, so it
    takes those alone; any other entry also takes every path that resolves to it or beneath it.
    """
    spelled_through = Path(os.path.abspath(path)).is_relative_to(os.path.abspath(removed))
    if spelled_through or removed.is_symlink():
        return spelled_through

    return is_within(path, removed)
