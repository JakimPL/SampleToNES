from typing import Protocol


class DocumentState(Protocol):
    """The minimal state needed to title a document: a name and a dirty flag."""

    @property
    def name(self) -> str: ...

    @property
    def unsaved_changes(self) -> bool: ...


def _marked(state: DocumentState, untitled: str) -> str:
    name = state.name or untitled
    return f"{name}*" if state.unsaved_changes else name


def document_title(
    project: DocumentState,
    reconstruction: DocumentState,
    *,
    untitled: str,
    project_open: bool,
    reconstruction_loaded: bool,
) -> str:
    """
    Compose the application title from the active documents.

    When a project is open it is the primary document; a loaded reconstruction
    is appended as secondary after an em dash. When no project is open the
    reconstruction (if any) becomes the sole document in the title.
    """
    if project_open:
        title = _marked(project, untitled)
        if reconstruction_loaded:
            title = f"{title} — {_marked(reconstruction, untitled)}"
        return title

    if reconstruction_loaded:
        return _marked(reconstruction, untitled)

    return ""


def is_any_unsaved(project: DocumentState, reconstruction: DocumentState) -> bool:
    return project.unsaved_changes or reconstruction.unsaved_changes
