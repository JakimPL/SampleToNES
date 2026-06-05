from __future__ import annotations

from collections.abc import Hashable
from typing import Protocol, TypeVar, runtime_checkable

from .indexed import IndexedCollection


@runtime_checkable
class Identifiable(Hashable, Protocol):
    """An object carrying a stable, globally unique string identity."""

    id: str


IdentifiableT = TypeVar("IdentifiableT", bound=Identifiable)


class IdentifiedCollection(IndexedCollection[IdentifiableT]):
    """An :class:`IndexedCollection` keyed by each item's stable ``id``.

    The generic collection keys items by ``f"{hash(item):x}"``, which is a salted,
    truncated hash unusable for lookup by a known identifier. Here the key is the
    item's ``id`` itself: uuids are unique, so they are collision-free keys, and
    ``collection[id]`` / ``collection.get(id)`` / ``collection.get_index(id)`` all
    resolve in O(1). Stored references therefore stay readable ids and still resolve
    in constant time.

    Identity is the contract: two items sharing an ``id`` are the same entity (a
    duplicate insert raises). When an item's content changes such that it is a
    different entity, it receives a new ``id`` and is substituted.
    """

    @staticmethod
    def hash(item: IdentifiableT) -> str:
        return item.id
