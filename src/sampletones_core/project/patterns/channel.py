from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.structures import IndexedCollection

from .pattern import Pattern


class Channel(BaseModel):
    """One NES channel track.

    Owns a private pool of patterns, reusable within the channel and an order
    list that arranges them into the song. The order references patterns by
    their ``id``, so reordering the pool never invalidates the arrangement.
    The same pattern id may appear multiple times in the order.
    """

    generator: GeneratorName = Field(..., description="The NES channel this track drives.")
    patterns: IndexedCollection[Pattern] = Field(..., description="Reusable pattern pool.")
    order: List[str] = Field(..., description="Sequence of pattern ids forming the arrangement.")

    @classmethod
    def empty(cls, generator: GeneratorName, rows_per_pattern: int) -> Channel:
        pattern = Pattern.empty(rows_per_pattern)
        patterns: IndexedCollection[Pattern] = IndexedCollection([pattern])
        return cls(generator=generator, patterns=patterns, order=[pattern.id])

    def pattern(self, pattern_id: str) -> Pattern:
        for pattern in self.patterns:
            if pattern.id == pattern_id:
                return pattern

        raise KeyError(f"Pattern '{pattern_id}' not found in channel {self.generator}")

    def ordered_patterns(self) -> List[Pattern]:
        return [self.pattern(pattern_id) for pattern_id in self.order]

    def __repr__(self) -> str:
        return f"Channel(generator={self.generator}, patterns={len(self.patterns)}, order={len(self.order)})"
