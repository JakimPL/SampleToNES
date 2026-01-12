from typing import Dict, Generic, Optional, TypeVar, Union, cast

ValueT = TypeVar("ValueT")
KeyOrValue = Union[str, ValueT]


class BidirectionalHashMap(Generic[ValueT]):
    """
    A generic bidirectional hash map that maps strings to values of type T and vice versa.
    Assumes a bijective mapping between strings and values of type T, different than string.

    Internally, it maintains two dictionaries that store the forward and backward mappings.

    Inserting a new key-value pair updates both dictionaries. If a key or value already exists,
    it raises a ValueError unless it is being updated to the same value/key. Keys must be strings,
    and values must be of any typ different than string.

    Subscript item retrieval and assignment support both directions.

    Examples:
        ```
        bidirectional = BidirectionalHashMap()
        bidirectional["a"] = 1
        bidirectional["b"] = 2
        bidirectional["b"] = 3  # Updates the value for key "b"

        bidirectional.pop("a")  # Removes the key "a" and its associated value 1
        bidirectional.pop(3)    # Removes the value 3 and its associated key "b"
        bidirectional.pop("c")  # Raises KeyError
        ```
    """

    def __init__(self) -> None:
        self._forward: Dict[str, ValueT] = {}
        self._backward: Dict[ValueT, str] = {}

    def __getitem__(self, key: Union[str, ValueT]) -> Optional[Union[str, ValueT]]:
        if isinstance(key, str) and key in self._forward:
            return self._forward[key]

        if key in self._backward:
            return self._backward[cast(ValueT, key)]

        raise KeyError(f"Key {key} not found in either direction")

    def __setitem__(self, key: KeyOrValue, value: KeyOrValue) -> None:
        if isinstance(key, str):
            self.set_forward(key, cast(ValueT, value))
        else:
            self.set_backward(cast(ValueT, key), cast(str, value))

    def __delitem__(self, key: Union[str, ValueT]) -> None:
        if isinstance(key, str):
            value = self._forward.pop(key)
            del self._backward[value]
        else:
            string = self._backward.pop(cast(ValueT, key))
            del self._forward[string]

    def __len__(self) -> int:
        return len(self._forward)

    def __repr__(self) -> str:
        return f"BidirectionalHashMap({self._forward})"

    def _assign(self, key: str, value: ValueT) -> None:
        self._forward[key] = value
        self._backward[value] = key

    def set_forward(self, key: str, value: ValueT) -> None:
        if not isinstance(key, str):
            raise TypeError(f"Key must be a str, got {type(key)}")

        if isinstance(value, str):
            raise TypeError(f"Value must not be a str, got {type(value)}")

        if value in self._backward:
            original_key = self._backward[value]
            if original_key != key:
                raise ValueError(f"Value {value} is already mapped to the key {original_key}")

        if key in self._forward:
            del self._backward[self._forward[key]]

        self._assign(key, value)

    def set_backward(self, value: ValueT, key: str) -> None:
        if not isinstance(key, str):
            raise TypeError(f"Key must be a str, got {type(key)}")

        if isinstance(value, str):
            raise TypeError(f"Value must not be a str, got {type(value)}")

        if key in self._forward:
            original_key = self._forward[key]
            if original_key != value:
                raise ValueError(f"Key {key} is already bound to the value {original_key}")

        if value in self._backward:
            del self._forward[self._backward[value]]

        self._assign(key, value)

    def forward(self, key: str) -> ValueT:
        if not isinstance(key, str):
            raise TypeError(f"Key must be a str, got {type(key)}")

        return self._forward[key]

    def backward(self, value: ValueT) -> str:
        return self._backward[value]

    def get(self, key: Union[str, ValueT]) -> Optional[Union[str, ValueT]]:
        if isinstance(key, str) and key in self._forward:
            return self._forward.get(key)

        if key in self._backward:
            return self._backward.get(cast(ValueT, key))

        return None

    def pop(self, key: Union[str, ValueT]) -> Optional[Union[str, ValueT]]:
        if isinstance(key, str) and key in self._forward:
            return self.pop_forward(key)

        if key in self._backward:
            return self.pop_backward(cast(ValueT, key))

        raise KeyError(f"Key {key} not found in either direction")

    def pop_forward(self, key: str) -> ValueT:
        value = self._forward.pop(key)
        del self._backward[value]
        return value

    def pop_backward(self, value: ValueT) -> str:
        string = self._backward.pop(value)
        del self._forward[string]
        return string

    def remap_forward(self, old_key: str, new_key: str) -> None:
        value = self._forward.pop(old_key)
        self.set_forward(new_key, value)

    def remap_backward(self, old_value: ValueT, new_value: ValueT) -> None:
        string = self._backward.pop(old_value)
        self.set_backward(new_value, string)
