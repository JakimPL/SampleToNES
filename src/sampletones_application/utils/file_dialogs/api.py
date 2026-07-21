from pathlib import Path
from typing import Iterable, Optional, Tuple

from sampletones_application.utils.file_dialogs.filter import (
    FileFilter,
    normalize_extensions,
)
from sampletones_application.utils.file_dialogs.selection import (
    select_file_dialog_backend,
)
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.system.paths import ensure_suffix, to_path


def open_file_dialog(
    *,
    title: str,
    initial_directory: Optional[Pathlike] = None,
    extensions: Iterable[str] = (),
    filter_name: Optional[str] = None,
) -> Optional[Path]:
    backend = select_file_dialog_backend()
    return backend.open_file(
        title=title,
        initial_directory=_optional_path(initial_directory),
        file_filter=_build_filter(normalize_extensions(extensions), filter_name),
    )


def save_file_dialog(
    *,
    title: str,
    initial_directory: Optional[Pathlike] = None,
    default_filename: Optional[str] = None,
    extensions: Iterable[str] = (),
    filter_name: Optional[str] = None,
) -> Optional[Path]:
    patterns = normalize_extensions(extensions)
    backend = select_file_dialog_backend()
    path = backend.save_file(
        title=title,
        initial_directory=_optional_path(initial_directory),
        suggested_name=default_filename,
        file_filter=_build_filter(patterns, filter_name),
    )

    if path is None:
        return None

    if len(patterns) == 1:
        path = ensure_suffix(path, patterns[0].removeprefix("*"))

    return path


def select_directory_dialog(
    *,
    title: str,
    initial_directory: Optional[Pathlike] = None,
) -> Optional[Path]:
    backend = select_file_dialog_backend()
    return backend.select_directory(
        title=title,
        initial_directory=_optional_path(initial_directory),
    )


def _optional_path(value: Optional[Pathlike]) -> Optional[Path]:
    return to_path(value) if value is not None else None


def _build_filter(
    patterns: Tuple[str, ...],
    filter_name: Optional[str],
) -> Optional[FileFilter]:
    if not patterns:
        return None

    return FileFilter(name=filter_name or "", patterns=patterns)
