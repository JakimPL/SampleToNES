from dataclasses import dataclass
from typing import Optional

from sampletones_application.tags.general import SUF_BUTTON
from sampletones_shared.types.callback import VoidCallback


@dataclass(frozen=True)
class FocusStop:
    """One stop in a dialog's focus ring.

    ``focus_tag`` is the item :func:`dpg.focus_item` targets, ``enabled_tag`` the item whose
    enabled state gates the stop, and ``activate`` the Enter action for a button. Fields and
    combos leave ``activate`` empty so Enter stays with the control (Enter in the multiline
    comment inserts a line break, and a text-input dialog keeps its own submit-on-Enter).
    """

    focus_tag: str
    enabled_tag: str
    activate: Optional[VoidCallback]

    @classmethod
    def button(cls, tag: str, activate: VoidCallback) -> "FocusStop":
        """Builds a stop for a :class:`GUIButton`, focusing its inner button item."""
        return cls(focus_tag=f"{tag}{SUF_BUTTON}", enabled_tag=tag, activate=activate)

    @classmethod
    def field(cls, tag: str) -> "FocusStop":
        """Builds a stop for a text field or combo, which owns Enter itself."""
        return cls(focus_tag=tag, enabled_tag=tag, activate=None)
