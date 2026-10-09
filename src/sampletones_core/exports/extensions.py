from typing import Mapping, Optional

from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.scope import ExportScope


def format_for_extension(
    backends: Mapping[ExportFormat, ExportBackend],
    scope: ExportScope,
    extension: str,
) -> Optional[ExportFormat]:
    """The format whose ``scope`` files carry ``extension``.

    The destination the user names decides which format the export is written in, so the
    extension it ends in resolves to a format here. Case folds, letting a destination typed
    in capitals reach the same backend.

    Args:
        backends: Every backend the application writes through, keyed by its format.
        scope: The scope about to be exported.
        extension: The extension the chosen destination carries, leading dot included.

    Returns:
        Optional[ExportFormat]: The format claiming ``extension``, or ``None`` when no
        format able to express ``scope`` writes it.
    """
    wanted = extension.casefold()
    for export_format, backend in backends.items():
        if scope in backend.supported_scopes and backend.extension(scope).casefold() == wanted:
            return export_format

    return None
