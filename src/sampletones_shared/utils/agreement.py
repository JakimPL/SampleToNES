from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass
from typing import FrozenSet, Generic, Iterable, TypeVar

ValueT = TypeVar("ValueT", bound=Hashable)


@dataclass(frozen=True)
class Agreement(Generic[ValueT]):
    """Whether a group of sources holds one value in common.

    Three outcomes are kept apart: the group is empty, every source holds the same
    value, or the sources hold differing ones. Reporting the agreed value separately
    from the fact of agreement is what lets an absent value count as agreement — a
    transpose every channel leaves empty is a value they share.
    """

    distinct: FrozenSet[ValueT]

    @classmethod
    def collapse(cls, values: Iterable[ValueT]) -> Agreement[ValueT]:
        return cls(distinct=frozenset(values))

    @property
    def is_absent(self) -> bool:
        return not self.distinct

    @property
    def is_unanimous(self) -> bool:
        return len(self.distinct) == 1

    @property
    def is_mixed(self) -> bool:
        return len(self.distinct) > 1

    @property
    def value(self) -> ValueT:
        """The value every source holds.

        Raises:
            ValueError: if the group is empty or its sources differ, so that no
                single value describes them.
        """
        if not self.is_unanimous:
            raise ValueError(f"Agreement over {len(self.distinct)} distinct values holds no single value")

        return next(iter(self.distinct))

    def resolve(self, *, absent: ValueT, mixed: ValueT) -> ValueT:
        """The agreed value, or the stand-in named for the outcome that reached instead."""
        if self.is_absent:
            return absent

        if self.is_mixed:
            return mixed

        return self.value
