from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row


class Channel(BaseModel):
    """Pattern pool for one NES channel.

    Owns a private pool of patterns keyed by their integer index, reusable across
    any order position that references them. The same index may appear several times
    in the song's order; editing the pattern at a reused index affects every position
    that references it.

    The song's order list (not this class) determines which pattern plays at each
    position and how many positions exist.
    """

    generator: GeneratorName = Field(..., description="The NES channel this pool drives.")
    patterns: Dict[int, Pattern] = Field(..., description="Pattern pool keyed by index.")

    @classmethod
    def empty(cls, generator: GeneratorName, rows_per_pattern: int) -> Channel:
        return cls(generator=generator, patterns={0: Pattern.empty(rows_per_pattern)})

    def pattern(self, index: int) -> Optional[Pattern]:
        return self.patterns.get(index)

    def _next_index(self) -> int:
        return max(self.patterns, default=-1) + 1

    def add_pattern(self, length: int, *, name: Optional[str] = None) -> int:
        index = self._next_index()
        self.patterns[index] = Pattern.empty(length, name=name)
        return index

    def ensure_pattern(self, index: int, length: int) -> Pattern:
        """Returns the pattern at ``index``, creating an empty one if absent.

        Lets an order position reference an index before its pattern exists; the
        pattern is materialised on first write (once the slot gains content).
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
        del self.patterns[index]

    def get_row(self, index: int, row_index: int) -> Row:
        return self.patterns[index].rows[row_index]

    def set_row(self, index: int, row_index: int, row: Row) -> None:
        self.patterns[index].rows[row_index] = row

    def __repr__(self) -> str:
        return f"Channel(generator={self.generator}, patterns={len(self.patterns)})"
