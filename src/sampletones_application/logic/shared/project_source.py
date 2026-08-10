import copy
from dataclasses import dataclass
from typing import Dict, Protocol, Self

from sampletones_core.project import Project


def snapshot_project(project: Project) -> Project:
    """Captures an independent copy of a project that shares reconstruction audio.

    The song, settings, metadata and sample shells are deep-copied so later edits
    to the live project leave the snapshot untouched. Each sample's reconstruction
    is shared by reference, so the snapshot reuses those multi-megabyte audio
    arrays. Reconstruction edits are copy-on-write — each installs a fresh
    reconstruction — so the shared reconstruction stays valid for the life of the
    snapshot.
    """
    shared_reconstructions: Dict[int, object] = {
        id(sample.reconstruction): sample.reconstruction for sample in project.samples
    }
    return copy.deepcopy(project, shared_reconstructions)


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
        """Takes the document ``source`` currently holds, copied through :func:`snapshot_project`."""
        return cls(project=snapshot_project(source.project))
