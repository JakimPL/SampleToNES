from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final


@dataclass(frozen=True)
class TreeFilter:
    """What a browser is currently asked to show, held by the panel showing it.

    Several browsers render one tree, so what each of them narrows to belongs to the panel: a query
    typed in one tab leaves the other reading as it was. A filter is stated whole and replaced whole,
    so the panel resolves what it shows in one place.
    """

    query: str

    @property
    def is_active(self) -> bool:
        """Whether the filter narrows what the browser shows."""
        return bool(self.query)

    def with_query(self, query: str) -> TreeFilter:
        """The filter reading a new query, keeping everything else it states."""
        return replace(self, query=query)


NO_FILTER: Final[TreeFilter] = TreeFilter(query="")
