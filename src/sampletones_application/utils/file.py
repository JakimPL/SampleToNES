import shutil
import sys
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
    Union,
    cast,
)

import filedialpy

from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.system.paths import ensure_suffix, normalize_path
from sampletones_shared.utils.system.system import System

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


def _uses_zenity() -> bool:
    """
    Reports whether filedialpy routes dialogs through zenity.

    filedialpy prefers zenity on Linux whenever it is on the ``PATH``, falling back
    to kdialog or tkinter otherwise. Its GTK file chooser expects each filter as
    ``NAME | PATTERN``, so detecting this lets the caller format the filter the way
    that backend renders correctly.

    Returns:
        bool: ``True`` when zenity is the active Linux backend.
    """
    return sys.platform == "linux" and shutil.which("zenity") is not None


def _dialog_filter(
    normalized_extensions: List[str],
) -> Optional[Union[str, List[str]]]:
    """
    Returns the extension filter in the shape the active filedialpy backend expects.

    Each backend consumes the filter differently:
    - macOS calls ``filter.split(" ")``, so it needs a single space-joined string.
    - zenity renders a filter as ``NAME | PATTERN`` and labels a nameless filter
      "(None)", so the patterns are supplied as both the name and the pattern list,
      collapsed into a single filter entry.
    - the remaining backends iterate the list of patterns directly.

    An empty selection yields ``None`` so every backend skips filtering.

    Args:
        normalized_extensions (List[str]): Extensions already prefixed with ``*``.

    Returns:
        Optional[Union[str, List[str]]]: The filter shaped for the active backend.
    """
    if not normalized_extensions:
        return None

    if System.current() is System.MACOS:
        return " ".join(normalized_extensions)

    if _uses_zenity():
        patterns = " ".join(normalized_extensions)
        return [f"{patterns} | {patterns}"]

    return normalized_extensions


def _discard_macos_cancel(path: Optional[Path]) -> Optional[Path]:
    """
    Maps a cancelled macOS file dialog back to "no selection".

    The macOS backend returns the current working directory when the user cancels
    a save or open-file dialog, whereas Linux and Windows return an empty string.
    A file dialog only ever yields a file path, so a result equal to the working
    directory means the dialog was dismissed. Other platforms pass through
    unchanged.

    Args:
        path (Optional[Path]): The normalized dialog result.

    Returns:
        Optional[Path]: ``None`` for a macOS cancellation, otherwise ``path``.
    """
    if path is None:
        return None

    if System.current() is System.MACOS and path.resolve() == Path.cwd().resolve():
        return None

    return path


def open_file_dialog(
    *,
    title: str,
    initial_dir: Optional[Pathlike] = None,
    initial_file: Optional[str] = None,
    extensions: Iterable[str] = (),
) -> Optional[Path]:
    normalized_extensions = _normalize_extensions(extensions)
    filepath: Optional[str] = filedialpy.openFile(
        title=title,
        initial_dir=str(initial_dir) if initial_dir else None,
        initial_file=initial_file,
        filter=_dialog_filter(normalized_extensions),
    )

    return _discard_macos_cancel(normalize_path(filepath))


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
        filter=_dialog_filter(normalized_extensions),
    )

    path = _discard_macos_cancel(normalize_path(filepath))
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
