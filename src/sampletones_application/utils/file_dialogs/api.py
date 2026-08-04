from itertools import chain
from pathlib import Path
from typing import Optional, Tuple

from sampletones_application.utils.file_dialogs.destination import SaveDestination
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_application.utils.file_dialogs.selection import (
    select_file_dialog_backend,
)
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.system.paths import ensure_suffix, to_path


def open_file_dialog(
    *,
    title: str,
    initial_directory: Optional[Pathlike] = None,
    filters: Tuple[FileFilter, ...] = (),
) -> Optional[Path]:
    backend = select_file_dialog_backend()
    return backend.open_file(
        title=title,
        initial_directory=_optional_path(initial_directory),
        filters=filters,
    )


def save_file_dialog(
    *,
    title: str,
    initial_directory: Optional[Pathlike] = None,
    default_filename: Optional[str] = None,
    filters: Tuple[FileFilter, ...] = (),
) -> Optional[Path]:
    """
    Asks for a destination to save to, yielding ``None`` once the dialog is dismissed.

    The answer carries one of the offered extensions, so a caller receives a destination it
    can write straight away and a caller reading the format out of the extension always
    finds one. ``filters`` is ordered, and its first type is the one the dialog opens on.
    """
    backend = select_file_dialog_backend()
    destination = backend.save_file(
        title=title,
        initial_directory=_optional_path(initial_directory),
        suggested_name=default_filename,
        filters=filters,
    )

    if destination is None:
        return None

    return _with_offered_extension(destination, filters)


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


def _with_offered_extension(
    destination: SaveDestination,
    filters: Tuple[FileFilter, ...],
) -> Path:
    """
    Returns the destination's path ending in an extension one of the offered types accepts.

    A name already carrying one of those extensions stands as it is, so typing an extension is
    how a type is named where a dialog reports none. Any other name takes the extension of the
    governing type: the one the dialog reported for a dialog whose selector carries the choice,
    and otherwise the type the dialog opened on.
    """
    offered = _offered_extensions(filters)
    if not offered:
        return destination.path

    if _carries_one_of(destination.path, offered):
        return destination.path

    return ensure_suffix(destination.path, _governing_extension(destination.file_type, offered))


def _governing_extension(
    file_type: Optional[FileFilter],
    offered: Tuple[str, ...],
) -> str:
    """The extension a name carrying none of the offered ones is saved under."""
    if file_type is not None and file_type.extensions:
        return file_type.extensions[0]

    return offered[0]


def _carries_one_of(
    path: Path,
    extensions: Tuple[str, ...],
) -> bool:
    name = path.name.lower()
    return any(name.endswith(extension.lower()) for extension in extensions)


def _offered_extensions(filters: Tuple[FileFilter, ...]) -> Tuple[str, ...]:
    """The extensions every offered type accepts, in the order the types are shown."""
    return tuple(chain.from_iterable(file_filter.extensions for file_filter in filters))


def _optional_path(value: Optional[Pathlike]) -> Optional[Path]:
    return to_path(value) if value is not None else None
