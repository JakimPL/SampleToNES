from typing import Protocol, TypeVar

from sampletones_application.ui.panels.sequencer.input.state import GridInputState

CursorT = TypeVar("CursorT")
RegionT = TypeVar("RegionT")
TargetT_contra = TypeVar("TargetT_contra", contravariant=True)


class EditGrid(Protocol[CursorT, RegionT, TargetT_contra]):
    """What a grid states to the edit surface built over it.

    The state carries the cursor and the selection a target is resolved from, and the grid states
    its own actions for a target the surface hands back. Whether the grid owns those gestures at
    this moment is the question its key scope already answers, so one predicate serves the keyboard
    and the menu alike.
    """

    def owns_keys(self) -> bool: ...

    def input_state(self) -> GridInputState[CursorT, RegionT]: ...

    def add_action_items(self, target: TargetT_contra) -> None: ...

    def commit_entry(self) -> None:
        """Writes the entry being typed into the cell the cursor stands on."""
