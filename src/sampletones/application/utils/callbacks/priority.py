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
        return (self.priority, self.frame, self.insertion_counter)

    def __lt__(self, other: CallbackPriority) -> bool:
        return self.order < other.order
