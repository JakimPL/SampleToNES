from typing import Dict

from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.registry import build_tracker_backends
from sampletones_player.export import NSFBackend


def build_export_backends() -> Dict[ExportFormat, ExportBackend]:
    """Builds every backend the application exports through.

    The reconstruction engine stands below the console player and owns the tracker formats
    alone, so the backend writing a program the console runs joins them here, where both
    packages are in reach. Everything the application offers to export in is keyed by its
    format in the result, so a menu entry, a file type and a shortcut all reach one backend.

    Returns:
        Dict[ExportFormat, ExportBackend]: Every backend, keyed by the format it writes.
    """
    return {
        **build_tracker_backends(),
        ExportFormat.NSF: NSFBackend(),
    }
