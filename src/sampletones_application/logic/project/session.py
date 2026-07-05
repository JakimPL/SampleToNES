from typing import Optional

from sampletones_shared.types.callback import VoidCallback


class ProjectSession:
    def __init__(self) -> None:
        self._name: Optional[str] = None
        self.unsaved_changes: bool = False
        self.on_state_changed: Optional[VoidCallback] = None

    @property
    def name(self) -> str:
        return self._name or ""

    @property
    def is_open(self) -> bool:
        return self._name is not None

    def mark_loaded(self, name: str) -> None:
        self._name = name
        self.unsaved_changes = False
        self._notify()

    def mark_updated(self) -> None:
        self.unsaved_changes = True
        self._notify()

    def mark_saved(self, name: Optional[str] = None) -> None:
        if name is not None:
            self._name = name

        self.unsaved_changes = False
        self._notify()

    def mark_closed(self) -> None:
        self._name = None
        self.unsaved_changes = False
        self._notify()

    def _notify(self) -> None:
        if self.on_state_changed is not None:
            self.on_state_changed()
