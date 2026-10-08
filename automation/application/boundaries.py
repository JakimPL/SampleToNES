from dataclasses import dataclass

from automation.boundaries.audio import OutputRecord
from automation.boundaries.dialogs import ScriptedFileDialogs
from automation.boundaries.errors import ErrorRecords
from automation.boundaries.highlights import TableHighlights
from automation.boundaries.reveals import FileManagerStandIn
from automation.boundaries.spawns import SpawnGuard
from automation.holds.base import Holds


@dataclass(frozen=True)
class Boundaries:
    """What stands between a scenario's application and the desktop around it."""

    dialogs: ScriptedFileDialogs
    errors: ErrorRecords
    spawns: SpawnGuard
    holds: Holds
    file_manager: FileManagerStandIn
    highlights: TableHighlights
    output: OutputRecord
