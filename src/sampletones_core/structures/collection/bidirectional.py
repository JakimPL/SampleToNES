from __future__ import annotations

from collections.abc import Hashable, ItemsView, KeysView, ValuesView
from typing import Dict, Generic, Iterator, Optional, TypeVar, Union, cast

ValueT = TypeVar("ValueT", bound=Hashable)
BidirectionalMapping = Union[
    Dict[str, ValueT],
    Dict[ValueT, str],
    Dict[Union[str, ValueT], Union[str, ValueT]],
]


class BidirectionalHashMap(Generic[ValueT]):
    """
    A generic bidirectional hash map that maps strings to values of type T and vice versa.
    Assumes a bijective mapping between strings and values of a hashable type T, different than string.

    Internally, it maintains two dictionaries that store the forward and backward mappings.

    Inserting a new key-value pair updates both dictionaries. If a key or value already exists,
    it raises a ValueError unless it is being updated to the same value/key. Keys must be strings,
    and values must be of any typ different than string.

    Subscript item retrieval and assignment support both directions.

    Examples:
        The following shows the basic usage of the BidirectionalHashMap.

        ```python
        bidirectional = BidirectionalHashMap()
        bidirectional["a"] = 1
        bidirectional["b"] = 2
        bidirectional["b"] = 3    # Updates the value for key "b" from 2 to 3
        bidirectional[4] = "c"    # Sets the mapping from value 4 to key "c"

        print(bidirectional["a"])          # Outputs: 1
        print(bidirectional[3])            # Outputs: "b"
        print(bidirectional.get("d"))      # Outputs: None
        print(bidirectional.forward("b"))  # Outputs: 3

        bidirectional.remap_forward("a", "d")  # Changes key "a" to "d"
        bidirectional.pop("a")                 # Removes the key "a" and its associated value 1
        bidirectional.pop(3)                   # Removes the value 3 and its associated key "b"; the map is now empty
        ```

        The following shows common possible error cases.

        ```python
        bidirectional = BidirectionalHashMap({"a": 1, "b": 3})

        bidirectional.pop("c")    # Raises KeyError as key "c" does not exist
        bidirectional[2] = 2      # Raises TypeError as value cannot be a string
        bidirectional["c"] = "d"  # Raises TypeError as value cannot be a string
        bidirectional["b"] = 1    # Raises ValueError as value 1 is already mapped to key "a"
        ```
    """

    def __init__(
        self,
        mapping: Optional[BidirectionalMapping[ValueT]] = None,
    ) -> None:
        """
        Initializes a BidirectionalHashMap, optionally with initial mappings.

        Args:
            mapping (Optional[BidirectionalMapping]): An optional dictionary
                containing initial key-value pairs. Can be:
                * forward mappings (str -> ValueT),
                * backward mappings (ValueT -> str),
                * or mixed bidirectional mappings.

        Raises:
            TypeError: If any key is not a string or any value is a string.
            ValueError: If any key or value already exists with a different mapping.
        """
        self._forward: Dict[str, ValueT] = {}
        self._backward: Dict[ValueT, str] = {}
        if mapping:
            self.update(mapping)

    def __getitem__(self, key_or_value: Union[str, ValueT]) -> Optional[Union[str, ValueT]]:
        """
        Retrieves a value by string key or a key by value.

        Args:
            key_or_value (Union[str, ValueT]): The string key (forward lookup) or value (backward lookup).

        Returns:
            Optional[Union[str, ValueT]]: The corresponding value (if key is str) or key (if value is ValueT).

        Raises:
            KeyError: If the key or value is not found in either direction.
        """
        if isinstance(key_or_value, str) and key_or_value in self._forward:
            return self._forward[key_or_value]

        if key_or_value in self._backward:
            value = cast(ValueT, key_or_value)
            return self._backward[value]

        raise KeyError(f"Key/value '{key_or_value}' not found in either direction")

    def __setitem__(self, key_or_value: Union[str, ValueT], value_or_key: Union[str, ValueT]) -> None:
        """
        Sets a mapping bidirectionally, automatically determining the direction.

        Args:
            key_or_value (Union[str, ValueT]): The string key (forward) or value (backward).
            value_or_key (Union[str, ValueT]): The value (if key is str) or key (if value is ValueT).

        Raises:
            TypeError: If the types of key and value are not as expected.
            ValueError: If the key or value already exists with a different mapping.
        """
        self.set(key_or_value, value_or_key)

    def __delitem__(self, key_or_value: Union[str, ValueT]) -> None:
        """
        Deletes a mapping by string key or value, removing both directions.

        Args:
            key_or_value (Union[str, ValueT]): The string key (forward) or value (backward) to remove.

        Raises:
            KeyError: If the key or value is not found in either direction.
        """
        if isinstance(key_or_value, str):
            value = self._forward.pop(key_or_value)
            del self._backward[value]
        else:
            string = self._backward.pop(key_or_value)
            del self._forward[string]

    def __eq__(self, other: object) -> bool:
        """
        Checks equality between this BidirectionalHashMap and another object.

        Args:
            other (object): The object to compare with.

        Returns:
            bool: True if the other object is a BidirectionalHashMap with the same
                forward and backward mappings, False otherwise.
        """
        if not isinstance(other, BidirectionalHashMap):
            return False

        return self._forward == other._forward and self._backward == other._backward

    def __len__(self) -> int:
        """
        Returns the number of mappings in the bidirectional map.

        Returns:
            int: The total count of key-value pairs.
        """
        return len(self._forward)

    def __iter__(self) -> Iterator[str]:
        """
        Returns an iterator over the forward keys.

        Yields:
            str: String keys in the forward mapping.
        """
        return iter(self._forward)

    def __next__(self) -> str:
        """
        Returns the next key in the forward mapping.

        Returns:
            str: The next string key.
        """
        return next(iter(self._forward))

    def __repr__(self) -> str:
        """
        Returns a string representation of the bidirectional map.

        Returns:
            str: A string in the format 'BidirectionalHashMap({key: value, ...})'.
        """
        return f"BidirectionalHashMap({self._forward})"

    def _assign(self, key: str, value: ValueT) -> None:
        """
        Internal method to assign a key-value mapping in both directions.

        Args:
            key (str): The string key.
            value (ValueT): The value to map.
        """
        self._forward[key] = value
        self._backward[value] = key

    def keys_forward(self) -> KeysView[str]:
        """
        Returns an iterator over the forward keys.

        Returns:
            KeysView[str]: An iterator over the keys.
        """
        return self._forward.keys()

    def keys_backward(self) -> KeysView[ValueT]:
        """
        Returns an iterator over the backward values.

        Returns:
            KeysView[ValueT]: An iterator over the values.
        """
        return self._backward.keys()

    def items_forward(self) -> ItemsView[str, ValueT]:
        """
        Returns an iterator over the forward items (key-value pairs).

        Returns:
            ItemsView[str, ValueT]: An iterator over (key, value) pairs.
        """
        return self._forward.items()

    def items_backward(self) -> ItemsView[ValueT, str]:
        """
        Returns an iterator over the backward items (value-key pairs).

        Returns:
            ItemsView[ValueT, str]: An iterator over (value, key) pairs.
        """
        return self._backward.items()

    def values_forward(self) -> ValuesView[ValueT]:
        """
        Returns an iterator over the forward values.

        Returns:
            ValuesView[ValueT]: An iterator over the values.
        """
        return self._forward.values()

    def values_backward(self) -> ValuesView[str]:
        """
        Returns an iterator over the backward keys.

        Returns:
            ValuesView[str]: An iterator over the keys.
        """
        return self._backward.values()

    def clear(self) -> None:
        """
        Clears all mappings from the bidirectional map.
        """
        self._forward.clear()
        self._backward.clear()

    def copy(self) -> BidirectionalHashMap[ValueT]:
        """
        Creates a shallow copy of the bidirectional map.

        Returns:
            BidirectionalHashMap[ValueT]: A new instance of BidirectionalHashMap with the same mappings.
        """
        return BidirectionalHashMap[ValueT](self._forward)

    def update(self, mapping: BidirectionalMapping[ValueT]) -> None:
        """
        Updates the map bidirectionally with multiple key-value pairs from a dictionary.

        Args:
            mapping (BidirectionalMapping): A dictionary containing key/value pairs,
                possibly in both directions.

        Raises:
            TypeError: If any key is not a string or any value is a string.
            ValueError: If any key or value already exists with a different mapping.
        """
        for key, value in mapping.items():
            self.set(key, value)

    def update_forward(self, mapping: Dict[str, ValueT]) -> None:
        """
        Updates the bidirectional map with multiple key-value pairs from a dictionary.

        Args:
            mapping (Dict[str, ValueT]): A dictionary containing string keys and values of type T.

        Raises:
            TypeError: If any key is not a string or any value is a string.
            ValueError: If any key or value already exists with a different mapping.
        """
        for key, value in mapping.items():
            self.set_forward(key, value)

    def update_backward(self, mapping: Dict[ValueT, str]) -> None:
        """
        Updates the bidirectional map with multiple value-key pairs from a dictionary.

        Args:
            mapping (Dict[ValueT, str]): A dictionary containing values and string keys.

        Raises:
            TypeError: If any key is not a string or any value is a string.
            ValueError: If any key or value already exists with a different mapping.
        """
        for value, key in mapping.items():
            self.set_backward(value, key)

    def set(self, key_or_value: Union[str, ValueT], value_or_key: Union[str, ValueT]) -> None:
        """
        Bidirectional set method that determines the direction based on the type of the key.

        Args:
            key_or_value (Union[str, ValueT]): The key or value to set.
            value_or_key (Union[str, ValueT]): The value or key to set.

        Raises:
            TypeError: If the types of key and value are not as expected.
            ValueError: If the key or value already exists with a different mapping.
        """
        if isinstance(key_or_value, str):
            value = cast(ValueT, value_or_key)
            self.set_forward(key_or_value, value)
        else:
            key = cast(str, value_or_key)
            self.set_backward(key_or_value, key)

    def set_forward(self, key: str, value: ValueT) -> None:
        """
        Sets the mapping from key to value in the forward direction.

        Args:
            key (str): The string key.
            value (ValueT): The value to map to.

        Raises:
            TypeError: If the key is not a string or the value is a string.
            ValueError: If the key or value already exists with a different mapping.
        """
        if not isinstance(key, str):
            raise TypeError(f"Key must be a str, got {type(key)}")

        if isinstance(value, str):
            raise TypeError("Value must not be a str")

        if value in self._backward:
            original_key = self._backward[value]
            if original_key != key:
                raise ValueError(f"Value {value} is already mapped to the key {original_key}")

        if key in self._forward:
            del self._backward[self._forward[key]]

        self._assign(key, value)

    def set_backward(self, value: ValueT, key: str) -> None:
        """
        Sets the mapping from value to key in the backward direction.

        Args:
            value (ValueT): The value to map from.
            key (str): The string key to map to.

        Raises:
            TypeError: If the key is not a string or the value is a string.
            ValueError: If the key or value already exists with a different mapping.
        """
        if not isinstance(key, str):
            raise TypeError(f"Key must be a str, got {type(key)}")

        if isinstance(value, str):
            raise TypeError("Value must not be a str")

        if key in self._forward:
            original_key = self._forward[key]
            if original_key != value:
                raise ValueError(f"Key {key} is already bound to the value {original_key}")

        if value in self._backward:
            del self._forward[self._backward[value]]

        self._assign(key, value)

    def get(self, key_or_value: Union[str, ValueT]) -> Optional[Union[str, ValueT]]:
        """
        Bidirectional get method that retrieves the value based on the type of the key.

        Args:
            key_or_value (Union[str, ValueT]): The key or value to retrieve.

        Returns:
            Optional[Union[str, ValueT]]: The corresponding value or key if found, else None.
        """
        if isinstance(key_or_value, str) and key_or_value in self._forward:
            return self._forward.get(key_or_value)

        if key_or_value in self._backward:
            return self._backward.get(cast(ValueT, key_or_value))

        return None

    def forward(self, key: str) -> ValueT:
        """
        Retrieves the value mapped to the given string key in the forward direction.

        Args:
            key (str): The string key.

        Returns:
            ValueT: The value mapped to the key.

        Raises:
            KeyError: If the key is not found.
            TypeError: If the key is not a string.
        """
        if not isinstance(key, str):
            raise TypeError(f"Key must be a str, got {type(key)}")

        return self._forward[key]

    def backward(self, value: ValueT) -> str:
        """
        Retrieves the string key mapped to the given value in the backward direction.

        Args:
            value (ValueT): The value.

        Returns:
            str: The string key mapped to the value.

        Raises:
            KeyError: If the value is not found.
        """
        return self._backward[value]

    def pop(self, key_or_value: Union[str, ValueT]) -> Optional[Union[str, ValueT]]:
        """
        Bidirectional pop method that removes and returns the value based on the type of the key.

        Args:
            key_or_value (Union[str, ValueT]): The key or value to remove.

        Returns:
            Optional[Union[str, ValueT]]: The corresponding value or key if found and removed, else None.

        Raises:
            KeyError: If the key is not found in either direction.
        """
        if isinstance(key_or_value, str) and key_or_value in self._forward:
            return self.pop_forward(key_or_value)

        if key_or_value in self._backward:
            return self.pop_backward(cast(ValueT, key_or_value))

        raise KeyError(f"Key/value '{key_or_value}' not found in either direction")

    def pop_forward(self, key: str) -> ValueT:
        """
        Removes and returns the value mapped to the given string key in the forward direction.

        Args:
            key (str): The string key.

        Returns:
            ValueT: The value that was mapped to the key.

        Raises:
            KeyError: If the key is not found.
        """
        value = self._forward.pop(key)
        del self._backward[value]
        return value

    def pop_backward(self, value: ValueT) -> str:
        """
        Removes and returns the string key mapped to the given value in the backward direction.

        Args:
            value (ValueT): The value.

        Returns:
            str: The string key that was mapped to the value.

        Raises:
            KeyError: If the value is not found.
        """
        string = self._backward.pop(value)
        del self._forward[string]
        return string

    def remap(
        self,
        old_key_or_value: Union[str, ValueT],
        new_key_or_value: Union[str, ValueT],
    ) -> None:
        """
        Remaps an existing key or value to a new key or value in the appropriate direction.

        Args:
            old_key_or_value (Union[str, ValueT]): The existing key or value to be remapped.
            new_key_or_value (Union[str, ValueT]): The new key or value to map to.

        Raises:
            KeyError: If the old_key_or_value is not found.
            TypeError: If the types of old_key_or_value and new_key_or_value do not match.
        """
        if isinstance(old_key_or_value, str) and isinstance(new_key_or_value, str):
            return self.remap_forward(old_key_or_value, new_key_or_value)

        if not isinstance(old_key_or_value, str) and not isinstance(new_key_or_value, str):
            return self.remap_backward(old_key_or_value, new_key_or_value)

        raise TypeError(
            "Both 'old_key_or_value' and 'new_key_or_value' must be of the same type (either str or ValueT)"
        )

    def remap_forward(self, old_key: str, new_key: str) -> None:
        """
        Remaps an existing key to a new key in the forward direction.

        Args:
            old_key (str): The existing string key to be remapped.
            new_key (str): The new string key to map to.

        Raises:
            KeyError: If the old_key is not found.
        """
        value = self.pop_forward(old_key)
        self.set_forward(new_key, value)

    def remap_backward(self, old_value: ValueT, new_value: ValueT) -> None:
        """
        Remaps an existing value to a new value in the backward direction.

        Args:
            old_value (ValueT): The existing value to be remapped.
            new_value (ValueT): The new value to map to.

        Raises:
            KeyError: If the old_value is not found.
        """
        string = self.pop_backward(old_value)
        self.set_backward(new_value, string)
