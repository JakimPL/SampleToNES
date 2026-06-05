from typing import Protocol


class DocumentState(Protocol):
    """The minimal state needed to title a document: a name and a dirty flag."""

    name: str
    unsaved_changes: bool


def _marked(state: DocumentState, untitled: str) -> str:
    name = state.name or untitled
    return f"{name}*" if state.unsaved_changes else name


def document_title(
    project: DocumentState,
    reconstruction: DocumentState,
    *,
    untitled: str,
    reconstruction_loaded: bool,
) -> str:
    """Compose the application title with the project as the primary document.

    The project always shows (its name, suffixed with ``*`` when unsaved). A loaded
    reconstruction is a secondary editor and is appended after an em dash. This
    encodes the precedence rule: the project takes precedence over the reconstruction.
    """
    title = _marked(project, untitled)
    if reconstruction_loaded:
        title = f"{title} — {_marked(reconstruction, untitled)}"

    return title


def is_any_unsaved(project: DocumentState, reconstruction: DocumentState) -> bool:
    """True when either document has unsaved changes (drives the exit confirmation)."""
    return project.unsaved_changes or reconstruction.unsaved_changes
