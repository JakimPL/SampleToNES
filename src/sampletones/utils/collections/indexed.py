from typing import Dict, Generic, Optional, TypeVar, Union

from pydantic import BaseModel

from sampletones.utils import hash_model

from .bidirectional import BidirectionalHashMap

T = TypeVar("T", bound=BaseModel)


class IndexedCollection(Generic[T]):
    def __init__(self) -> None:
        self._items: Dict[str, T] = {}
        self._order: BidirectionalHashMap[int] = BidirectionalHashMap()

    def __getitem__(self, key: Union[int, str]) -> T:
        if isinstance(key, int):
            return self._items[self._order.backward(key)]

        if isinstance(key, str):
            return self._items[key]

        raise TypeError(f"Index must be an int or str, got {type(key)}")

    def __repr__(self) -> str:
        return f"IndexedCollection({[
            self._items[self._order.backward(item)] for item in range(len(self._order))
        ]})"

    def get(self, key: Union[int, str]) -> Optional[T]:
        if isinstance(key, int):
            if key < 0 or key >= len(self._order):
                return None

            return self._items[self._order.backward(key)]

        if isinstance(key, str):
            return self._items.get(key)

        raise TypeError(f"Index must be an int or str, got {type(key)}")

    def add(self, item: T) -> None:
        self.insert(len(self._order), item)

    def _set(self, index: int, item_hash: str, item: T) -> int:
        self._items[item_hash] = item
        self._order[item_hash] = index
        return index

    def _unset(self, index: int) -> None:
        item = self._order.pop_backward(index)
        del self._items[item]

    def insert(self, index: int, item: T) -> None:
        if index < 0 or index > len(self._order):
            raise IndexError(f"Index {index} out of bounds for insert in IndexedCollection of size {len(self._order)}")

        item_hash = hash_model(item)
        if item_hash in self._items:
            return

        self._reindex(index, add=True)
        self._set(index, item_hash, item)

    def remove(self, index: int) -> None:
        self._unset(index)
        self._reindex(index, add=False)

    def _reindex(self, index: int, add: bool = True) -> None:
        for i in range(len(self._order), index, -1):
            if add:
                self._order.remap_backward(i - 1, i)
            else:
                self._order.remap_backward(i, i - 1)

    def order(self, key: str) -> Optional[int]:
        try:
            self._order.forward(key)
        except KeyError:
            pass
