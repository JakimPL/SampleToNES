import shutil
from pathlib import Path


def remove_path(path: Path) -> bool:
    """Removes what stands at ``path``, a directory with everything under it or a single file.

    Args:
        path: The file or directory.

    Returns:
        bool: Whether anything stood there.
    """
    if path.is_dir():
        shutil.rmtree(path)
        return True

    if path.exists():
        path.unlink()
        return True

    return False
