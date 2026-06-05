from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.structures import IdentifiedCollection

from .pattern import Pattern
from .row import Row


class Channel(BaseModel):
    """One NES channel track.

    Owns a private pool of patterns, reusable within the channel and an order
    list that arranges them into the song. The order references patterns by
    their ``id``, resolved in O(1) through the :class:`IdentifiedCollection`, so
    reordering the pool never invalidates the arrangement. The same pattern id
    may appear multiple times in the order.
    """

    generator: GeneratorName = Field(..., description="The NES channel this track drives.")
    patterns: IdentifiedCollection[Pattern] = Field(..., description="Reusable pattern pool, keyed by id.")
    order: List[str] = Field(..., description="Sequence of pattern ids forming the arrangement.")

    @classmethod
    def empty(cls, generator: GeneratorName, rows_per_pattern: int) -> Channel:
        pattern = Pattern.empty(rows_per_pattern)
        patterns: IdentifiedCollection[Pattern] = IdentifiedCollection([pattern])
        return cls(generator=generator, patterns=patterns, order=[pattern.id])

    def pattern(self, pattern_id: str) -> Pattern:
        return self.patterns[pattern_id]

    def ordered_patterns(self) -> List[Pattern]:
        return [self.patterns[pattern_id] for pattern_id in self.order]

    def add_pattern(self, length: int, *, name: Optional[str] = None) -> Pattern:
        pattern = Pattern.empty(length, name=name)
        self.patterns.append(pattern)
        return pattern

    def duplicate_pattern(self, pattern_id: str) -> Pattern:
        source = self.pattern(pattern_id)
        clone = Pattern(name=source.name, rows=list(source.rows))
        self.patterns.append(clone)
        return clone

    def remove_pattern(self, pattern_id: str) -> None:
        """Drops the pattern from the pool and purges every order reference to it.

        Patterns are referenced by id from the order list, so a removal that
        left stale ids behind would break :meth:`ordered_patterns`.
        """
        self.patterns.pop(pattern_id)
        self.order = [entry for entry in self.order if entry != pattern_id]

    def set_row(self, pattern_id: str, row_index: int, row: Row) -> None:
        self.pattern(pattern_id).rows[row_index] = row

    def append_to_order(self, pattern_id: str) -> None:
        self.pattern(pattern_id)
        self.order.append(pattern_id)

    def insert_into_order(self, index: int, pattern_id: str) -> None:
        self.pattern(pattern_id)
        self.order.insert(index, pattern_id)

    def remove_from_order(self, index: int) -> None:
        del self.order[index]

    def move_in_order(self, from_index: int, to_index: int) -> None:
        entry = self.order.pop(from_index)
        self.order.insert(to_index, entry)

    def __repr__(self) -> str:
        return f"Channel(generator={self.generator}, patterns={len(self.patterns)}, order={len(self.order)})"
