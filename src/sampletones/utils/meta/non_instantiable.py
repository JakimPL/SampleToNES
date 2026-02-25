from abc import ABCMeta
from typing import Any, Type, TypeVar

T = TypeVar("T")


class NonInstantiableMeta(ABCMeta):
    def __call__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        is_root = not any(isinstance(base, NonInstantiableMeta) for base in cls.__bases__)

        if is_root:
            raise TypeError(f"{cls.__name__} cannot be instantiated directly")

        instance: T = ABCMeta.__call__(cls, *args, **kwargs)
        return instance
