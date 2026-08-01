from sampletones_core.formats.famitracker.builder import project_to_module
from sampletones_core.formats.famitracker.module import module_to_ftm_bytes
from sampletones_core.project.project import Project
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import save_binary


def write_ftm(filepath: Pathlike, project: Project) -> None:
    """Exports a project to a FamiTracker ``.ftm`` module file."""
    module = project_to_module(project)
    save_binary(filepath, module_to_ftm_bytes(module))
