from typing import Protocol


class DocumentState(Protocol):
    """The minimal state needed to title a document: a name and a dirty flag."""

    @property
    def name(self) -> str: ...

    @property
    def unsaved_changes(self) -> bool: ...
