from typing import Protocol

from sampletones_core.exports.request import SampleExport
from sampletones_core.project.project import Project
from sampletones_player.export.program import NSFProgram


class ProgramChoice(Protocol):
    """Which program a request is written as.

    A request arriving through the export seam carries the work alone, so the program it is
    written under is decided beside it: either the one each source states for itself, or one the
    user settled before the run.
    """

    def for_sample(self, request: SampleExport) -> NSFProgram:
        """The program a reconstruction's slices are written as."""

    def for_project(self, project: Project) -> NSFProgram:
        """The program a whole composition is written as."""
