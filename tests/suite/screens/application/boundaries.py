from dataclasses import dataclass

from tests.suite.screens.boundaries.audio import OutputRecord
from tests.suite.screens.boundaries.dialogs import ScriptedFileDialogs
from tests.suite.screens.boundaries.errors import ErrorRecords
from tests.suite.screens.boundaries.highlights import TableHighlights
from tests.suite.screens.boundaries.reveals import FileManagerStandIn
from tests.suite.screens.boundaries.spawns import SpawnGuard
from tests.suite.screens.holds.base import Holds


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
