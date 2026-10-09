from sampletones_core.exports.request import SampleExport
from sampletones_core.project.project import Project
from sampletones_player.export.program import NSFProgram


class StatedProgram:
    """Writes each request as the program its own source states.

    This is what an export asks for when nobody set one up: the text, channels, repeat and
    compression :meth:`NSFProgram.for_sample` and :meth:`NSFProgram.for_project` state.
    """

    def for_sample(self, request: SampleExport) -> NSFProgram:
        return NSFProgram.for_sample(request)

    def for_project(self, project: Project) -> NSFProgram:
        return NSFProgram.for_project(project)
