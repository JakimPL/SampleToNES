from __future__ import annotations

from typing import AbstractSet, Dict, Optional

from pydantic import BaseModel, Field

from sampletones_core.constants.enums import ChannelName
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

    name: ChannelName = Field(..., description="The NES channel this pool drives.")
    patterns: Dict[int, Pattern] = Field(..., description="Pattern pool keyed by index.")

    @classmethod
    def empty(cls, name: ChannelName, rows_per_pattern: int) -> Channel:
        return cls(name=name, patterns={0: Pattern.empty(rows_per_pattern)})

    def pattern(self, index: int) -> Optional[Pattern]:
        return self.patterns.get(index)

    def _next_index(self, reserved_indices: AbstractSet[int] = frozenset()) -> int:
        """Returns a free index above every pool key and ``reserved_indices``.

        The pool alone does not reveal indices an order slot references before its
        pattern is materialised, so a caller aware of those passes them as
        ``reserved_indices`` to keep the new index from taking one of them.
        """
        return max(self.patterns.keys() | reserved_indices, default=-1) + 1

    def add_pattern(
        self,
        length: int,
        *,
        name: Optional[str] = None,
        reserved_indices: AbstractSet[int] = frozenset(),
    ) -> int:
        index = self._next_index(reserved_indices)
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

    def clone_pattern(self, index: int, *, reserved_indices: AbstractSet[int] = frozenset()) -> int:
        """Clones the pattern at ``index`` into a fresh index and returns that index.

        ``reserved_indices`` are extra indices the clone must avoid beyond the pool's
        own keys, so a caller that knows of indices referenced elsewhere (order slots
        whose patterns are not yet materialised) keeps the clone from taking one of them.
        """
        source = self.patterns[index]
        clone_index = self._next_index(reserved_indices)
        self.patterns[clone_index] = Pattern(name=source.name, rows=list(source.rows))
        return clone_index

    def remove_pattern(self, index: int) -> None:
        del self.patterns[index]

    def get_row(self, index: int, row_index: int) -> Row:
        return self.patterns[index].rows[row_index]

    def set_row(self, index: int, row_index: int, row: Row) -> None:
        self.patterns[index].rows[row_index] = row

    def __repr__(self) -> str:
        return f"Channel(name={self.name}, patterns={len(self.patterns)})"
