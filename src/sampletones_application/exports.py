from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.registry import build_tracker_backends
from sampletones_player.export.backend import NSFBackend


@dataclass(frozen=True)
class ExportBackends:
    """Every backend the application exports through.

    The reconstruction engine stands below the console player and owns the tracker formats
    alone, so the backend writing a program the console runs joins them here, where both
    packages are in reach. Everything the application offers to export in is keyed by its
    format in :attr:`by_format`, so a menu entry, a file type and a shortcut all reach one
    backend, and the console player's backend is named as well, since the NSF export setup binds
    that same backend to the program it chooses.

    Attributes:
        nsf: The backend writing console programs.
        trackers: The backends writing the tracker formats, keyed by the format each writes.
    """

    nsf: NSFBackend
    trackers: Dict[ExportFormat, ExportBackend]

    @classmethod
    def build(cls) -> ExportBackends:
        """Builds every backend, reading the resources each writes with.

        Raises:
            OSError: If the console player's packaged driver is absent.
        """
        return cls(
            nsf=NSFBackend.stated(),
            trackers=build_tracker_backends(),
        )

    @property
    def by_format(self) -> Dict[ExportFormat, ExportBackend]:
        """Every backend, keyed by the format it writes."""
        return {
            **self.trackers,
            ExportFormat.NSF: self.nsf,
        }
