from enum import Enum, auto
from typing import Optional, Tuple

from pydantic import BaseModel


class SampleEntryViewModel(BaseModel, frozen=True):
    sample_id: str
    name: str
    loop: bool


class SequencerSamplesViewModel(BaseModel, frozen=True):
    """The ordered sample pool shown in the right-hand samples panel."""

    samples: Tuple[SampleEntryViewModel, ...]


class MoveDirection(Enum):
    """A reorder action offered for a sample in the instruments context menu."""

    UP = auto()
    DOWN = auto()
    TOP = auto()
    BOTTOM = auto()

    def target(self, position: int, count: int) -> Optional[int]:
        """Resolve the destination index, or ``None`` when the move cannot be performed.

        ``None`` is the grey-out signal: moving up/to-top from the first row or
        down/to-bottom from the last row would not change anything, so the menu
        disables that item.
        """
        match self:
            case MoveDirection.UP:
                return position - 1 if position > 0 else None
            case MoveDirection.DOWN:
                return position + 1 if position < count - 1 else None
            case MoveDirection.TOP:
                return 0 if position > 0 else None
            case MoveDirection.BOTTOM:
                return count - 1 if position < count - 1 else None
