from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from sampletones_core.constants.enums import GeneratorName

from .pattern import Pattern
from .row import Row


class Channel(BaseModel):
    """One NES channel track.

    Owns a private pool of patterns keyed by their integer index, reusable within
    the channel, and an order list that arranges them into the song by index. The
    same index may appear several times in the order; editing the pattern at a
    reused index affects every position that references it.
    """

    generator: GeneratorName = Field(..., description="The NES channel this track drives.")
    patterns: Dict[int, Pattern] = Field(..., description="Pattern pool keyed by index.")
    order: List[Optional[int]] = Field(
        ...,
        description="Arrangement: each position is a pattern index, or None for an empty slot.",
    )

    @classmethod
    def empty(cls, generator: GeneratorName, rows_per_pattern: int) -> Channel:
        return cls(generator=generator, patterns={0: Pattern.empty(rows_per_pattern)}, order=[0])

    def pattern(self, index: int) -> Optional[Pattern]:
        """Resolves an order index to its pattern, or ``None`` for an empty slot.

        An order position may reference an index with no pattern in the pool (e.g.
        after the pattern was removed). ``None`` represents that empty slot, so the
        arrangement keeps its length and the order table stays aligned.
        """
        return self.patterns.get(index)

    def ordered_patterns(self) -> List[Optional[Pattern]]:
        return [self.patterns.get(index) if index is not None else None for index in self.order]

    def _next_index(self) -> int:
        return max(self.patterns, default=-1) + 1

    def add_pattern(self, length: int, *, name: Optional[str] = None) -> int:
        index = self._next_index()
        self.patterns[index] = Pattern.empty(length, name=name)
        return index

    def ensure_pattern(self, index: int, length: int) -> Pattern:
        """Returns the pattern at ``index``, creating an empty one if absent.

        Lets an order position reference an index that has no pattern yet; the
        pattern is materialised on first write (when the slot is no longer empty).
        """
        if index not in self.patterns:
            self.patterns[index] = Pattern.empty(length)

        return self.patterns[index]

    def duplicate_pattern(self, index: int) -> int:
        source = self.patterns[index]
        clone_index = self._next_index()
        self.patterns[clone_index] = Pattern(name=source.name, rows=list(source.rows))
        return clone_index

    def remove_pattern(self, index: int) -> None:
        """Drops the pattern from the pool and empties the positions that used it.

        Order references to the removed index are rewritten to ``None`` *in place*
        (same positions, just emptied), so the arrangement keeps its length and the
        order table's columns stay aligned across channels. Rewriting to ``None``
        rather than leaving the stale index also prevents a later :meth:`add_pattern`
        — which reuses the freed index — from accidentally refilling those slots.
        """
        del self.patterns[index]
        self.order = [None if entry == index else entry for entry in self.order]

    def get_row(self, index: int, row_index: int) -> Row:
        return self.patterns[index].rows[row_index]

    def set_row(self, index: int, row_index: int, row: Row) -> None:
        self.patterns[index].rows[row_index] = row

    def append_to_order(self, index: Optional[int]) -> None:
        self.order.append(index)

    def insert_into_order(self, position: int, index: Optional[int]) -> None:
        self.order.insert(position, index)

    def set_in_order(self, position: int, index: Optional[int]) -> None:
        self.order[position] = index

    def remove_from_order(self, position: int) -> None:
        del self.order[position]

    def move_in_order(self, from_position: int, to_position: int) -> None:
        entry = self.order.pop(from_position)
        self.order.insert(to_position, entry)

    def __repr__(self) -> str:
        return f"Channel(generator={self.generator}, patterns={len(self.patterns)}, order={len(self.order)})"
