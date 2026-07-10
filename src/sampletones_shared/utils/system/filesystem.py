import shutil
from pathlib import Path

from sampletones_shared.types.path import Pathlike

from .paths import to_path


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
