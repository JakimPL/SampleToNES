from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class CallbackPriority:
    priority: int
    frame: int
    insertion_counter: int

    @property
    def order(self) -> Tuple[int, int, int]:
        """Sort key with the target frame as the primary component.

        ``CallbackQueue`` drains in this order and reads dueness off the heap
        top, so the earliest target frame must sort first for a not-yet-due top
        to mean nothing is due. Within a single frame, lower priority numbers
        run first, then earlier insertion.
        """
        return (
            self.frame,
            self.priority,
            self.insertion_counter,
        )

    def __lt__(self, other: CallbackPriority) -> bool:
        return self.order < other.order
