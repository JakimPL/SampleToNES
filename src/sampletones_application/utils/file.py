from functools import wraps
from pathlib import Path
from typing import (
    Callable,
    Concatenate,
    Iterable,
    List,
    Optional,
    ParamSpec,
    TypeVar,
    cast,
)

import filedialpy

from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.system.paths import ensure_suffix, normalize_path

P = ParamSpec("P")
T = TypeVar("T")


def _normalize_path(
    func: Callable[P, Optional[str]],
) -> Callable[P, Optional[Path]]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Optional[Path]:
        filepath: Optional[str] = func(*args, **kwargs)
        return normalize_path(filepath)

    return wrapper


def ignore_none_path(
    func: Callable[Concatenate[T, Path, P], None],
) -> Callable[Concatenate[T, Path | None, P], None]:
    @wraps(func)
    def wrapper(
        self: T,
        filepath: Path | None,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        if filepath is None:
            return

        func(self, filepath, *args, **kwargs)

    return cast(
        Callable[Concatenate[T, Path | None, P], None],
        wrapper,
    )


def _normalize_extensions(extensions: Iterable[str]) -> List[str]:
    return [f"*{extension.removeprefix('*')}" for extension in extensions]


@_normalize_path
def open_file_dialog(
    *,
    title: str,
    initial_dir: Optional[Pathlike] = None,
    initial_file: Optional[str] = None,
    extensions: Iterable[str] = (),
) -> Optional[str]:
    normalized_extensions = _normalize_extensions(extensions)
    filepath: Optional[str] = filedialpy.openFile(
        title=title,
        initial_dir=str(initial_dir) if initial_dir else None,
        initial_file=initial_file,
        filter=list(normalized_extensions),
    )

    return filepath


def save_file_dialog(
    *,
    title: str,
    initial_dir: Optional[Pathlike] = None,
    default_filename: Optional[str] = None,
    extensions: Iterable[str] = (),
) -> Optional[Path]:
    normalized_extensions = _normalize_extensions(extensions)
    filepath: Optional[str] = filedialpy.saveFile(
        title=title,
        initial_dir=str(initial_dir) if initial_dir else None,
        initial_file=default_filename,
        filter=normalized_extensions,
    )

    path = normalize_path(filepath)
    if path is None:
        return None

    if len(normalized_extensions) == 1:
        path = ensure_suffix(
            path,
            normalized_extensions[0].removeprefix("*"),
        )

    return path


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
