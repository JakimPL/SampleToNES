from typing import Optional

from sampletones_shared.types.callback import VoidCallback


class ProjectSession:
    """Tracks the current project's name and unsaved-changes state.

    Mirrors :class:`ReconstructionSession`. The project is the primary document;
    the application shell combines this with the reconstruction session to compose
    the window title and the exit/unsaved flow (see :mod:`title`).
    """

    def __init__(self) -> None:
        self.name: str = ""
        self.unsaved_changes: bool = False
        self.on_state_changed: Optional[VoidCallback] = None

    def mark_loaded(self, name: str) -> None:
        self.name = name
        self.unsaved_changes = False
        self._notify()

    def mark_updated(self) -> None:
        self.unsaved_changes = True
        self._notify()

    def mark_saved(self, name: Optional[str] = None) -> None:
        if name is not None:
            self.name = name

        self.unsaved_changes = False
        self._notify()

    def mark_closed(self) -> None:
        self.name = ""
        self.unsaved_changes = False
        self._notify()

    def _notify(self) -> None:
        if self.on_state_changed is not None:
            self.on_state_changed()
