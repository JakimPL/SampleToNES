from abc import ABCMeta
from typing import Any, Type, TypeVar

T = TypeVar("T")


class NonInstantiableMeta(ABCMeta):
    """Metaclass that reserves a base class as abstract while its subclasses instantiate.

    The class that first applies this metaclass is treated as the root and rejects
    direct construction; any subclass of it constructs normally. This marks a
    hierarchy's top type as usable only through its concrete descendants.
    """

    def __call__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        """Constructs an instance of a subclass of the root type.

        Raises:
            TypeError: If called on the root class that first applied this metaclass.
        """
        is_root = not any(isinstance(base, NonInstantiableMeta) for base in cls.__bases__)

        if is_root:
            raise TypeError(f"{cls.__name__} cannot be instantiated directly")

        instance: T = ABCMeta.__call__(cls, *args, **kwargs)
        return instance
