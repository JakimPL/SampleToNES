from functools import wraps
from pathlib import Path
from typing import Callable, Iterable, Optional, ParamSpec, TypeVar

import filedialpy

from sampletones_shared.types.application import Sender
from sampletones_shared.types.data import SerializedData
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.system.paths import normalize_path, to_path

P = ParamSpec("P")
T = TypeVar("T")


def file_dialog_handler(
    func: Callable[[T, Path], None],
) -> Callable[[T, int, SerializedData], None]:
    @wraps(func)
    def wrapper(self: T, sender: Sender, app_data: SerializedData) -> None:
        if not app_data or "file_path_name" not in app_data:
            return

        filepath = app_data["file_path_name"]
        if not filepath:
            return

        filepath = to_path(filepath)
        func(self, filepath)

    return wrapper


def _normalize_path(
    func: Callable[P, Optional[str]],
) -> Callable[P, Optional[Path]]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Optional[Path]:
        filepath: Optional[str] = func(*args, **kwargs)
        return normalize_path(filepath)

    return wrapper


@_normalize_path
def open_file_dialog(
    *,
    title: str,
    initial_dir: Optional[Pathlike] = None,
    initial_file: Optional[str] = None,
    extensions: Iterable[str] = (),
) -> Optional[str]:
    filepath: Optional[str] = filedialpy.openFile(
        title=title,
        initial_dir=str(initial_dir) if initial_dir else None,
        initial_file=initial_file,
        filter=list(extensions),
    )

    return filepath


@_normalize_path
def save_file_dialog(
    *,
    title: str,
    initial_dir: Optional[Pathlike] = None,
    default_filename: Optional[str] = None,
    extensions: Iterable[str] = (),
) -> Optional[str]:
    filepath: Optional[str] = filedialpy.saveFile(
        title=title,
        initial_dir=str(initial_dir) if initial_dir else None,
        initial_file=default_filename,
        filter=list(extensions),
    )

    return filepath


@_normalize_path
def select_directory_dialog(
    *,
    title: str,
    initial_dir: Optional[Pathlike] = None,
) -> Optional[str]:
    filepath: Optional[str] = filedialpy.openDir(
        title=title,
        initial_dir=str(initial_dir) if initial_dir else None,
    )

    return filepath
