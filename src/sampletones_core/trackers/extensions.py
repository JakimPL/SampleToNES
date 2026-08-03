from typing import Mapping, Optional, Tuple

from sampletones_core.trackers.backend import TrackerBackend
from sampletones_core.trackers.format import TrackerFormat
from sampletones_core.trackers.scope import ExportScope


def scope_extensions(
    backends: Mapping[TrackerFormat, TrackerBackend],
    scope: ExportScope,
) -> Tuple[str, ...]:
    """The extensions a destination for ``scope`` may carry, leading dot included.

    One export action reaches every format able to express the scope, so the dialog that
    picks a destination offers all of their extensions at once and the chosen one names
    the format. Each extension appears once, in the order the backends were registered.

    Args:
        backends: Every backend the application writes through, keyed by its format.
        scope: The scope about to be exported.

    Returns:
        Tuple[str, ...]: The extension of each format that can express ``scope``.
    """
    extensions = (backend.extension(scope) for backend in backends.values() if scope in backend.supported_scopes)
    return tuple(dict.fromkeys(extensions))


def format_for_extension(
    backends: Mapping[TrackerFormat, TrackerBackend],
    scope: ExportScope,
    extension: str,
) -> Optional[TrackerFormat]:
    """The format whose ``scope`` files carry ``extension``.

    The destination the user names decides which tracker the export is written for, so
    the extension it ends in resolves to a format here. Case folds, letting a destination
    typed in capitals reach the same backend.

    Args:
        backends: Every backend the application writes through, keyed by its format.
        scope: The scope about to be exported.
        extension: The extension the chosen destination carries, leading dot included.

    Returns:
        Optional[TrackerFormat]: The format claiming ``extension``, or ``None`` when no
        format able to express ``scope`` writes it.
    """
    wanted = extension.casefold()
    for tracker_format, backend in backends.items():
        if scope in backend.supported_scopes and backend.extension(scope).casefold() == wanted:
            return tracker_format

    return None
