from typing import Optional, Protocol

from sampletones_application.logic.project.controller import ProjectController


class SampleDirectory(Protocol):
    """The samples a note can name, read the way a grid prints them: by list position."""

    def position_of(self, sample_id: str) -> Optional[int]: ...

    def sample_at(self, position: int) -> Optional[str]: ...


class ProjectSampleDirectory:
    """The samples the open project holds, in the order the samples panel lists them.

    The project is read on each lookup, because opening a document and every undo put another
    one in place, so a block stated as text names whichever sample stands at that position now.
    """

    def __init__(self, project_controller: ProjectController) -> None:
        self._controller = project_controller

    def position_of(self, sample_id: str) -> Optional[int]:
        """Where a sample stands in the list, present while the project holds it."""
        samples = self._controller.project.samples
        if samples.get(sample_id) is None:
            return None

        return samples.get_index(sample_id)

    def sample_at(self, position: int) -> Optional[str]:
        """The sample a position names, present while the list reaches that far."""
        samples = self._controller.project.samples
        if 0 <= position < len(samples):
            return samples[position].id

        return None
