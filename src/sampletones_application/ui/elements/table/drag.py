from collections.abc import Hashable
from dataclasses import dataclass
from typing import Generic, TypeVar

KeyT = TypeVar("KeyT", bound=Hashable)


@dataclass
class DragGesture(Generic[KeyT]):
    """The press a drag selection grows from.

    ``origin`` is the cell the button went down on, which is the end a plain drag anchors its
    selection at. ``extends`` records that the press held Shift, so the drag carries the
    selection already on the grid instead of starting a new one. ``moved`` states that the
    pointer has reached another cell, which is what tells a drag apart from a click: until it
    is set, the press is still a click and the selection is left alone.
    """

    origin: KeyT
    extends: bool
    moved: bool = False
