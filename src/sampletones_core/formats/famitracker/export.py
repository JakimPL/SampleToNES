from sampletones_core.exporters.skipped import BuiltDocument
from sampletones_core.formats.famitracker.builder import build_module
from sampletones_core.formats.famitracker.model.module import FamiTrackerModule
from sampletones_core.formats.famitracker.module import module_to_ftm_bytes
from sampletones_core.project.project import Project
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import save_binary


def write_ftm(filepath: Pathlike, project: Project) -> BuiltDocument[FamiTrackerModule]:
    """Exports a project to a FamiTracker ``.ftm`` module file.

    Returns:
        BuiltDocument[FamiTrackerModule]: The module written, the rows written as a note cut
        because their voice has no instrument on the channel, and the instruments a sequence
        shortened.
    """
    built = build_module(project)
    save_binary(filepath, module_to_ftm_bytes(built.document))
    return built
