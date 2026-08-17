from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final


@dataclass(frozen=True)
class TreeFilter:
    """What a browser is currently asked to show, held by the panel showing it.

    Several browsers render one tree, so what each of them narrows to belongs to the panel: a query
    typed in one tab leaves the other reading as it was. A filter is stated whole and replaced whole,
    so the panel resolves what it shows in one place.

    The two criteria answer different questions: the query decides which of the rows on screen are
    shown, while showing favorites alone decides which rows are drawn at all.
    """

    query: str
    favorites_only: bool

    @property
    def is_active(self) -> bool:
        """Whether the filter narrows what the browser shows."""
        return bool(self.query) or self.favorites_only

    def with_query(self, query: str) -> TreeFilter:
        """The filter reading a new query, keeping everything else it states."""
        return replace(self, query=query)

    def with_favorites_only(self, favorites_only: bool) -> TreeFilter:
        """The filter showing the favorites alone or the whole tree, keeping the query it states."""
        return replace(self, favorites_only=favorites_only)


NO_FILTER: Final[TreeFilter] = TreeFilter(
    query="",
    favorites_only=False,
)
