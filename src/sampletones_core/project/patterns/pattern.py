from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from .row import Row


class Pattern(BaseModel):
    """A reusable block of rows belonging to a single channel.

    Mutable so its rows and name can be edited in place. A pattern's identity is
    its integer key within the owning channel's pattern dictionary, so the model
    itself carries no id; the same key may be referenced from several order
    positions, and editing the pattern there changes every position at once.
    """

    name: Optional[str] = Field(default=None, description="Optional human-readable name.")
    rows: List[Row] = Field(..., description="Tracker lines, in order.")

    @classmethod
    def empty(cls, length: int, name: Optional[str] = None) -> Pattern:
        return cls(rows=[Row() for _ in range(length)], name=name)

    @property
    def length(self) -> int:
        return len(self.rows)

    def is_empty(self) -> bool:
        return all(row.is_empty() for row in self.rows)

    def __repr__(self) -> str:
        return f"Pattern(name={self.name!r}, length={self.length})"
