from __future__ import annotations

from typing import (
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
    TypeVar,
    Union,
    overload,
)

from sampletones_shared.types.data import ModelHashable

from .bidirectional import BidirectionalHashMap

T = TypeVar("T", bound=ModelHashable)


class IndexedCollection(Generic[T]):
    """
    A generic collection that maintains both positional order and hash-based access,
    for immutable hashable objects. Each item is stored with a unique hash, preventing duplicates
    while maintaining stable integer indices. The collection thus does not allow duplicate items
    (items with the same hash).

    Collection items should not be changed in a way that affects their hash while they are
    stored in the collection. Doing so may lead to inconsistent behavior.

    Internally, this class uses a dictionary for item storage and a BidirectionalHashMap to track the
    mapping between item hashes and their positional indices. When items are inserted or removed,
    only the affected indices are updated, and the hashes remain stable.

    Subscript access supports both integer indices (including negative indices) and hash strings.
    Items are uniquely identified by their hash, computed via the calculate_hash function.

    Item membership can be checked using the `in` operator, which checks for the presence of an item
    based on its hash, not its position nor equality.

    Examples:
        The following shows basic usage of IndexedCollection.

        ```python
        collection = IndexedCollection(["apple", "banana", "cherry"])

        print(collection[0])               # Outputs: "apple"
        print(collection[-1])              # Outputs: "cherry"
        print(len(collection))             # Outputs: 3

        collection.append("date")
        collection.insert(1, "blueberry")

        item = collection.pop(0)           # Removes and returns first item: "apple"
        collection.remove("banana")        # Removes by value

        print("cherry" in collection)      # Outputs: True

        for item in collection:
            print(item)                    # Iterates through items in order
        ```

        The following shows hash-based access.

        ```python
        collection = IndexedCollection()
        item = "test_item"
        collection.append(item)

        item_hash = IndexedCollection.hash(item)
        print(collection[item_hash])       # Access by hash string: "test_item"
        print(collection.index(item))      # Get index of item: 0

        collection[item_hash] = "updated_item"  # Replace by hash
        ```

        The following shows common error cases.

        ```python
        collection = IndexedCollection(["apple"])

        collection.append("apple")         # Raises ValueError: duplicate item
        collection[5]                      # Raises IndexError: out of bounds
        collection.pop()                   # Removes last item: "apple"
        collection.pop()                   # Raises IndexError: pop from empty
        collection.remove("banana")        # Raises ValueError: not found
        ```
    """

    def __init__(self, collection: Optional[Iterable[T]] = None) -> None:
        """
        Initializes an IndexedCollection, optionally with items from an iterator.

        Args:
            collection (Optional[Iterable[T]]): An optional iterable of items to initialize the collection.
                Items are added in the order they are yielded. Duplicate items will raise ValueError.

        Raises:
            ValueError: If the collection contains duplicate items (items with the same hash).
        """
        self._items: Dict[str, T] = {}
        self._order: BidirectionalHashMap[int] = BidirectionalHashMap()
        if collection:
            self.extend(collection)

    @overload
    def __getitem__(self, key: int) -> T: ...

    @overload
    def __getitem__(self, key: str) -> T: ...

    @overload
    def __getitem__(self, key: slice) -> IndexedCollection[T]: ...

    def __getitem__(self, key: Union[int, str, slice]) -> Union[T, IndexedCollection[T]]:
        """
        Retrieves an item by integer index, hash string, or slice.

        Args:
            key (Union[int, str, slice]): The integer index (supports negative indices),
                hash string, or slice object.

        Returns:
            Union[T, IndexedCollection[T]]: The item at the specified position/hash,
                or a new IndexedCollection containing the sliced items.

        Raises:
            IndexError: If the integer index is out of bounds.
            KeyError: If the hash string is not found.
            TypeError: If the key is not an int, str, or slice.
        """
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            items: List[T] = [self[i] for i in range(start, stop, step)]
            return IndexedCollection[T](items)

        item_hash = self.get_hash(key)
        return self._items[item_hash]

    def __delitem__(self, key: Union[int, str]) -> None:
        """
        Deletes an item by integer index or hash string.

        Args:
            key (Union[int, str]): The integer index (supports negative indices) or hash string.

        Raises:
            IndexError: If the integer index is out of bounds.
            KeyError: If the hash string is not found.
            TypeError: If the key is neither an int nor a str.
        """
        index = self.get_index(key)
        self._unset(index)

    def __setitem__(self, key: Union[int, str], item: T) -> None:
        """
        Replaces the item at the specified position or hash with a new item.

        If the new item already exists elsewhere in the collection, raises ValueError,
        unless it is at the same position being replaced. In such case, the replacement
        does take place anyway, as hash equality does not imply object equality.

        Args:
            key (Union[int, str]): The integer index (supports negative indices) or hash string.
            item (T): The new item to set at the specified position.

        Raises:
            IndexError: If the integer index is out of bounds.
            KeyError: If the hash string is not found.
            ValueError: If the new item already exists at a different position.
            TypeError: If the key is neither an int nor a str.
        """
        index = self.get_index(key)
        item_hash = self.hash(item)

        if item_hash in self._items:
            if self._order.forward(item_hash) != index:
                raise ValueError(f"Item '{item!r}' already exists in IndexedCollection")

        self._unset(index, reindex=False)
        self._set(index, item_hash, item, reindex=False)

    def __bool__(self) -> bool:
        """
        Returns True if the collection is not empty.

        Returns:
            bool: True if the collection contains at least one item, False otherwise.
        """
        return len(self._order) > 0

    def __eq__(self, value: object) -> bool:
        """
        Checks equality between this collection and another object.


        Args:
            value (object): The object to compare against.

        Returns:
            bool: True if the other object is an IndexedCollection,
                with items of the same hash in the same order, False otherwise.
        """
        if not isinstance(value, IndexedCollection):
            return False

        if len(self) != len(value):
            return False

        for index in range(len(self)):
            if self.get_hash(index) != value.get_hash(index):
                return False

        return True

    def __contains__(self, item: T) -> bool:
        """
        Checks if an item exists in the collection.

        Args:
            item (T): The item to check for membership.

        Returns:
            bool: True if the item is in the collection, False otherwise.
        """
        return self.hash(item) in self._items

    def __iter__(self) -> Iterator[T]:
        """
        Returns an iterator over the items in the collection in positional order.

        Yields:
            T: Items in the collection from index 0 to len(collection)-1.
        """
        for index in range(len(self._order)):
            yield self._items[self._order.backward(index)]

    def __next__(self) -> T:
        """
        Returns the next item in the iteration.

        Returns:
            T: The next item in the collection.

        Raises:
            StopIteration: If there are no more items to iterate over.
        """
        return next(self.__iter__())

    def __len__(self) -> int:
        """
        Returns the number of items in the collection.

        Returns:
            int: The total count of items.
        """
        return len(self._order)

    def __repr__(self) -> str:
        """
        Returns a string representation of the collection.

        Returns:
            str: A string in the format 'IndexedCollection([item1, item2, ...])'
        """
        return f"IndexedCollection({list(self)})"

    def get(self, key: Union[int, str], default: Optional[T] = None) -> Optional[T]:
        """
        Retrieves an item by integer index or hash string, returning a default value if not found.

        Args:
            key (Union[int, str]): The integer index (supports negative indices) or hash string.
            default (Optional[T]): The value to return if the key is not found. Defaults to None.

        Returns:
            Optional[T]: The item if found, otherwise the default value.

        Raises:
            TypeError: If the key is neither an int nor a str.
        """
        if isinstance(key, int):
            try:
                key = self.get_hash(key)
            except (IndexError, KeyError):
                return default

        elif not isinstance(key, str):
            raise TypeError(f"Key must be a position (int) or a hash (str), got {type(key)}")

        return self._items.get(key, default)

    def clear(self) -> None:
        """
        Removes all items from the collection.
        """
        self._items.clear()
        self._order.clear()

    def copy(self) -> IndexedCollection[T]:
        """
        Creates a shallow copy of the collection.

        Returns:
            IndexedCollection[T]: A new IndexedCollection with the same items in the same order.
        """
        return IndexedCollection[T](item for item in self)

    def append(self, item: T) -> None:
        """
        Adds an item to the end of the collection.

        Args:
            item (T): The item to append.

        Raises:
            ValueError: If an item with the same hash already exists in the collection.
        """
        self.insert(len(self._order), item)

    def extend(self, items: Iterable[T]) -> None:
        """
        Extends the collection by appending items from an iterable.

        Args:
            items (Iterable[T]): An iterable of items to append.

        Raises:
            ValueError: If any item with the same hash already exists in the collection.
        """
        for item in items:
            self.append(item)

    def insert(self, index: int, item: T) -> None:
        """
        Inserts an item at the specified index position.

        All items at or after the specified index are shifted to the right.

        Args:
            index (int): The position to insert at. Must be in range [0, len(collection)].
            item (T): The item to insert.

        Raises:
            IndexError: If the index is out of bounds.
            ValueError: If an item with the same hash already exists in the collection.
        """
        if index < 0 or index > len(self._order):
            raise IndexError(f"Index {index} out of bounds in IndexedCollection of size {len(self._order)}")

        item_hash = self.hash(item)
        if item_hash in self._items:
            raise ValueError(f"Item '{item!r}' already exists in IndexedCollection")

        self._set(index, item_hash, item)

    def pop(self, key: Union[int, str] = -1) -> T:
        """
        Removes and returns an item by integer index or hash string.

        Args:
            key (Union[int, str]): The integer index (supports negative indices) or hash string.
                Defaults to -1 (last item).

        Returns:
            T: The removed item.

        Raises:
            IndexError: If the collection is empty or the integer index is out of bounds.
            KeyError: If the hash string is not found.
            TypeError: If the key is neither an int nor a str.
        """
        if not bool(self):
            raise IndexError("Pop from empty IndexedCollection")

        index = self.get_index(key)
        item = self._items[self._order.backward(index)]
        self._unset(index)
        return item

    def remove(self, item: T) -> None:
        """
        Removes the first occurrence of an item from the collection.

        Args:
            item (T): The item to remove.

        Raises:
            ValueError: If the item is not found in the collection.
        """
        index = self.index(item)
        self._unset(index)

    def index(self, item: T) -> int:
        """
        Returns the index of the first occurrence of an item.

        Args:
            item (T): The item to find.

        Returns:
            int: The zero-based index of the item.

        Raises:
            ValueError: If the item is not found in the collection.
        """
        item_hash = self.hash(item)
        try:
            return self._order.forward(item_hash)
        except KeyError as exception:
            raise ValueError(f"Item '{item!r}' not found in IndexedCollection") from exception

    @staticmethod
    def hash(item: T) -> str:
        """
        Computes the hash string for an item.

        Args:
            item (T): The item to hash.

        Returns:
            str: The hash string uniquely identifying the item.
        """
        return f"{hash(item):x}"

    @property
    def hashes(self) -> List[str]:
        """
        Returns an iterator over the hash strings of the items in positional order.

        Returns:
            List[str]: A list of hash strings from index 0 to len(collection)-1.
        """
        return [self._order.backward(index) for index in range(len(self._order))]

    def _wrap_index(self, index: int) -> int:
        """
        Converts a potentially negative index to a valid positive index.

        Args:
            index (int): The index to wrap. Negative indices count from the end.

        Returns:
            int: The wrapped non-negative index.

        Raises:
            IndexError: If the wrapped index is out of bounds.
        """
        if index < 0:
            index += len(self._order)

        if index < 0 or index >= len(self._order):
            raise IndexError(f"Index {index} out of bounds in IndexedCollection of size {len(self._order)}")

        return index

    def get_hash(self, key: Union[int, str]) -> str:
        """
        Converts an integer index or validates a hash string key, returning the hash.

        Args:
            key (Union[int, str]): The integer index (supports negative indices) or hash string.

        Returns:
            str: The hash string corresponding to the key.

        Raises:
            IndexError: If the integer index is out of bounds.
            KeyError: If the hash string is not found.
            TypeError: If the key is neither an int nor a str.
        """
        if isinstance(key, int):
            index = self._wrap_index(key)
            return self._order.backward(index)

        if not isinstance(key, str):
            raise TypeError(f"Key must be a position (int) or a hash (str), got {type(key)}")

        if key not in self._items:
            raise KeyError(f"Hash '{key}' not found in IndexedCollection")

        return key

    def get_index(self, key: Union[int, str]) -> int:
        """
        Converts an integer index or hash string key to an integer index.

        Args:
            key (Union[int, str]): The integer index (supports negative indices) or hash string.

        Returns:
            int: The zero-based index corresponding to the key.

        Raises:
            IndexError: If the integer index is out of bounds.
            KeyError: If the hash string is not found.
            TypeError: If the key is neither an int nor a str.
        """
        if isinstance(key, int):
            return self._wrap_index(key)

        if not isinstance(key, str):
            raise TypeError(f"Key must be a position (int) or a hash (str), got {type(key)}")

        return self._order.forward(key)

    def _set(self, index: int, item_hash: str, item: T, reindex: bool = True) -> int:
        """
        Internal method to add an item at a specific index.

        Args:
            index (int): The index position to set.
            item_hash (str): The hash string of the item.
            item (T): The item to store.
            reindex (bool): Whether to shift indices at or after this position. Defaults to True.

        Returns:
            int: The index where the item was set.
        """
        if reindex:
            self._reindex(index, add=True)

        self._items[item_hash] = item
        self._order[item_hash] = index
        return index

    def _unset(self, index: int, reindex: bool = True) -> None:
        """
        Internal method to remove an item at a specific index.

        Args:
            index (int): The index position to remove.
            reindex (bool): Whether to shift indices after this position. Defaults to True.
        """
        item = self._order.pop_backward(index)
        del self._items[item]

        if reindex:
            self._reindex(index, add=False)

    def _reindex(self, index: int, add: bool = True) -> None:
        """
        Internal method to shift indices when items are inserted or removed.

        Args:
            index (int): The position where the insert/remove operation occurred.
            add (bool): If True, shifts indices to the right (for insertion).
                If False, shifts indices to the left (for removal). Defaults to True.
        """
        if add:
            for i in range(len(self._order), index, -1):
                self._order.remap_backward(i - 1, i)
        else:
            for i in range(index + 1, len(self._order) + 1):
                self._order.remap_backward(i, i - 1)
