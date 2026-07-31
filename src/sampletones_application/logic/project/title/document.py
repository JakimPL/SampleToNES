from dataclasses import dataclass
from typing import Optional

from sampletones_application.logic.project.title.compose import join_segments
from sampletones_application.logic.project.title.state import DocumentState


@dataclass(frozen=True)
class ReconstructionTitlePart:
    """The reconstruction segment of the title, resolved for one render.

    ``included`` marks a reconstruction that belongs to the open project as a sample:
    it is shown in brackets to signal membership, and the project's own dirty marker
    covers it. A standalone (file-backed) reconstruction is shown as its own title segment
    and carries its own dirty marker, because it is an independent document.
    """

    name: str
    unsaved_changes: bool
    included: bool


def _mark(name: str, unsaved_changes: bool) -> str:
    return f"{name}*" if unsaved_changes else name


def _marked(state: DocumentState, untitled: str) -> str:
    return _mark(state.name or untitled, state.unsaved_changes)


def document_title(
    project: DocumentState,
    reconstruction: Optional[ReconstructionTitlePart],
    *,
    untitled: str,
    project_open: bool,
) -> str:
    """
    Compose the application title from the active documents.

    When a project is open it is the primary document. A reconstruction that is part
    of the project is appended in brackets; a standalone reconstruction is appended as a
    separate segment. When no project is open the reconstruction becomes the sole document
    in the title.
    """
    if project_open:
        title = _marked(project, untitled)
        if reconstruction is not None:
            if reconstruction.included:
                title = f"{title} [{reconstruction.name}]"
            else:
                marked = _mark(
                    reconstruction.name,
                    reconstruction.unsaved_changes,
                )
                title = join_segments(title, marked)

        return title

    if reconstruction is not None:
        return _mark(reconstruction.name, reconstruction.unsaved_changes)

    return ""
