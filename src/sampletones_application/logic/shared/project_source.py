from dataclasses import dataclass
from typing import Protocol, Self

from sampletones_core.project import Project


class ProjectSource(Protocol):
    """Where a reader of the open document finds the project it works on.

    A reader of the song needs the project and nothing else about where it came from.
    :class:`~sampletones_application.logic.project.controller.ProjectController` satisfies this, so
    playback follows every edit as it is made; :class:`ProjectSnapshot` satisfies it too, so a long
    operation describes the document as it stood when it was asked for. Depending on this protocol
    is what lets one synthesis kernel serve both.
    """

    @property
    def project(self) -> Project: ...


@dataclass(frozen=True)
class ProjectSnapshot:
    """One project held still, the document a long operation reads.

    A render walks the whole song on a worker thread while the user keeps editing. Reading a
    snapshot makes the result describe one state of the document: the state it was requested in,
    from the first row to the last.

    Attributes:
        project: The document as it stood when the snapshot was taken.
    """

    project: Project

    @classmethod
    def capture(cls, source: ProjectSource) -> Self:
        """Takes the document ``source`` currently holds, through :meth:`Project.snapshot`."""
        return cls(project=source.project.snapshot())
