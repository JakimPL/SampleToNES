from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from .row import Row


class Pattern:
    """A reusable block of rows belonging to a single channel.

    Mutable so its rows and name can be edited in place, but its identity is
    anchored to a uuid ``id`` generated once at construction. The hash never
    changes under mutation, satisfying the invariant required to store patterns
    in an :class:`IndexedCollection`. References from a channel order list use
    this stable ``id``, never the collection position.
    """

    def __init__(self, rows: List[Row], name: Optional[str] = None) -> None:
        self.id: str = uuid4().hex
        self.name: Optional[str] = name
        self.rows: List[Row] = rows

    @classmethod
    def empty(cls, length: int, name: Optional[str] = None) -> Pattern:
        return cls(rows=[Row() for _ in range(length)], name=name)

    @property
    def length(self) -> int:
        return len(self.rows)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Pattern) and self.id == other.id

    def __repr__(self) -> str:
        return f"Pattern(id={self.id!r}, name={self.name!r}, length={self.length})"
