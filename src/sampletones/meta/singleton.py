import threading
from typing import Any, Dict, Optional, Tuple, Type, TypeVar

T = TypeVar("T")


class SingletonMeta(type):
    _lock: threading.Lock = threading.Lock()

    def __init__(cls, name: str, bases: Tuple[Type[Any], ...], namespace: Dict[str, Any]) -> None:
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
        return cls._instances.get(cls)

    def has_instance(cls) -> bool:
        return cls in cls._instances

    def clear_instances(cls) -> None:
        with cls._instance_lock:
            cls._instances.clear()

    def clear_instance(cls, target_cls: Type[Any]) -> None:
        with cls._instance_lock:
            cls._instances.pop(target_cls, None)
