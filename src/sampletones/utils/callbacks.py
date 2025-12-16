from typing import Any, Callable, Optional, ParamSpec, TypeVar

from sampletones.typehints import Callback

P = ParamSpec("P")
R = TypeVar("R")


class CallbackMixin:
    def call(self, callback: Optional[Callable[P, R]], *args: Any, **kwargs: Any) -> Optional[R]:
        if callback is None:
            return None

        if not callable(callback):
            raise TypeError("Provided callback is not callable")

        return callback(*args, **kwargs)

    def set_callbacks(
        self,
        **callbacks: Optional[Callback],
    ) -> None:
        for name, callback in callbacks.items():
            if callback is not None and callable(callback):
                setattr(self, name, callback)
