import threading
from typing import Any, Dict, Optional, Tuple, Type, TypeVar

from sampletones_shared.types.data import SerializedData

T = TypeVar("T")


class SingletonMeta(type):
    """Metaclass that yields one shared instance per class.

    A class built with this metaclass returns the same instance on every
    construction. The first construction is guarded by a per-class lock with a
    double-checked pattern, so threads that race to create it still end up sharing
    one instance. The registry helpers support tests that reset that shared state.
    """

    _lock: threading.Lock = threading.Lock()

    def __init__(
        cls,
        name: str,
        bases: Tuple[Type[Any], ...],
        namespace: SerializedData,
    ) -> None:
        super().__init__(name, bases, namespace)
        cls._instances: Dict[Type[Any], Any] = {}
        cls._instance_lock: threading.Lock = threading.Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            with cls._instance_lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance

        return cls._instances[cls]

    def get_instance(cls) -> Optional[Any]:
        """Returns the shared instance once it has been created.

        Returns:
            Optional[Any]: The instance, or ``None`` if the class has yet to be constructed.
        """
        return cls._instances.get(cls)

    def has_instance(cls) -> bool:
        """Reports whether the shared instance has been created.

        Returns:
            bool: ``True`` once the class has been constructed at least once.
        """
        return cls in cls._instances

    def clear_instances(cls) -> None:
        """Discards every cached instance, so the next construction builds afresh."""
        with cls._instance_lock:
            cls._instances.clear()

    def clear_instance(cls, target_cls: Type[Any]) -> None:
        """Discards the cached instance for one class, when present.

        Args:
            target_cls (Type[Any]): The class whose cached instance is dropped.
        """
        with cls._instance_lock:
            cls._instances.pop(target_cls, None)
