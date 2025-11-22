import os
from pathlib import Path
from typing import Union


def shorten_path(path: Path, levels: int = 5) -> str:
    path = path.expanduser().resolve()
    parts = path.parts

    if len(parts) <= levels:
        return str(path)

    root = parts[0]
    first_dir = parts[1]
    last_parts = parts[-(levels - 2) :]

    return os.sep.join([root.rstrip(os.sep), first_dir, "..."] + list(last_parts))


def to_path(path: Union[str, Path]) -> Path:
    if not isinstance(path, (str, Path)):
        raise TypeError(f"Expected path to be str or Path, got {type(path)}")

    if isinstance(path, str):
        path = Path(path)

    return path


def get_directory(path: Union[str, Path]) -> Path:
    path = to_path(path)
    return path if path.is_dir() else path.parent
