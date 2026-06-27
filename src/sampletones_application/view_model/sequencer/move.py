from enum import Enum, auto
from typing import Optional


class MoveDirection(Enum):
    """A reorder action: move an item toward the start or end of its sequence.

    Shared by the instruments list (vertical) and the order table (horizontal);
    the axis-neutral names map to up/left (``PREVIOUS``), down/right (``NEXT``),
    top/start (``FIRST``) and bottom/end (``LAST``) at each call site.
    """

    PREVIOUS = auto()
    NEXT = auto()
    FIRST = auto()
    LAST = auto()

    def target(self, position: int, count: int) -> Optional[int]:
        """Resolve the destination index, or ``None`` when the move cannot be performed.

        ``None`` is the grey-out signal: moving toward the start from the first
        position, or toward the end from the last, would change nothing, so the
        menu disables that item.
        """
        match self:
            case MoveDirection.PREVIOUS:
                return position - 1 if position > 0 else None
            case MoveDirection.NEXT:
                return position + 1 if position < count - 1 else None
            case MoveDirection.FIRST:
                return 0 if position > 0 else None
            case MoveDirection.LAST:
                return count - 1 if position < count - 1 else None
