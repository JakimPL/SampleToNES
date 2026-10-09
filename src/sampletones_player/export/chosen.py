from sampletones_core.exports.request import SampleExport
from sampletones_core.project.project import Project
from sampletones_player.export.program import NSFProgram


class ChosenProgram:
    """Writes a request as the one program the user settled before the run.

    Attributes:
        program: The program the run writes.
    """

    def __init__(self, program: NSFProgram) -> None:
        self.program = program

    def for_sample(self, request: SampleExport) -> NSFProgram:  # pylint: disable=unused-argument
        return self.program

    def for_project(self, project: Project) -> NSFProgram:  # pylint: disable=unused-argument
        return self.program
