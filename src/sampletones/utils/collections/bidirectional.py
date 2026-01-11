from typing import Dict, Generic, Optional, TypeVar, Union, cast

T = TypeVar("T")


class BidirectionalHashMap(Generic[T]):
    def __init__(self) -> None:
        self._forward: Dict[str, T] = {}
        self._backward: Dict[T, str] = {}

    def __getitem__(self, key: Union[str, T]) -> Optional[Union[str, T]]:
        if isinstance(key, str) and key in self._forward:
            return self._forward[key]

        if key in self._backward:
            return self._backward[cast(T, key)]

        raise KeyError(f"Key {key} not found in either direction")

    def __setitem__(self, key: str, value: T) -> None:
        if value in self._backward:
            original_key = self._backward[value]
            if original_key != key:
                raise ValueError(f"Value {value} is already mapped to the key {original_key}")

        if key in self._forward:
            del self._backward[self._forward[key]]

        self._forward[key] = value
        self._backward[value] = key

    def __delitem__(self, key: Union[str, T]) -> None:
        if isinstance(key, str):
            value = self._forward.pop(key)
            del self._backward[value]
        else:
            string = self._backward.pop(cast(T, key))
            del self._forward[string]

    def __len__(self) -> int:
        return len(self._forward)

    def __repr__(self) -> str:
        return f"BidirectionalHashMap({self._forward})"

    def forward(self, key: str) -> T:
        if not isinstance(key, str):
            raise TypeError(f"Key must be a str, got {type(key)}")

        return self._forward[key]

    def backward(self, key: T) -> str:
        return self._backward[key]

    def get(self, key: Union[str, T]) -> Optional[Union[str, T]]:
        if isinstance(key, str) and key in self._forward:
            return self._forward.get(key)

        if key in self._backward:
            return self._backward.get(cast(T, key))

        return None

    def pop(self, key: Union[str, T]) -> Optional[Union[str, T]]:
        if isinstance(key, str) and key in self._forward:
            return self.pop_forward(key)

        if key in self._backward:
            return self.pop_backward(cast(T, key))

        raise KeyError(f"Key {key} not found in either direction")

    def pop_forward(self, key: str) -> T:
        value = self._forward.pop(key)
        del self._backward[value]
        return value

    def pop_backward(self, key: T) -> str:
        string = self._backward.pop(key)
        del self._forward[string]
        return string

    def remap_forward(self, old_key: str, new_key: str) -> None:
        value = self._forward.pop(old_key)
        self._forward[new_key] = value
        self._backward[value] = new_key

    def remap_backward(self, old_key: T, new_key: T) -> None:
        string = self._backward.pop(old_key)
        self._backward[new_key] = string
        self._forward[string] = new_key
