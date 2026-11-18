from sampletones_core.exports.request import SampleExport
from sampletones_core.project.project import Project
from sampletones_player.export.program import Program


class StatedProgram:
    """Writes each request as the program its own source states.

    This is what an export asks for when nobody set one up: the text, channels, repeat and
    compression :meth:`Program.for_sample` and :meth:`Program.for_project` state.
    """

    def for_sample(self, request: SampleExport) -> Program:
        return Program.for_sample(request)

    def for_project(self, project: Project) -> Program:
        return Program.for_project(project)
