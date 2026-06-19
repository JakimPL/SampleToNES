from __future__ import annotations

from typing import Any, NamedTuple, Tuple

from sampletones_application.utils.callbacks.priority import CallbackPriority
from sampletones_shared.types.callback import Callback
from sampletones_shared.types.data import SerializedData


class CallbackTask(NamedTuple):
    priority: CallbackPriority
    callback: Callback
    args: Tuple[Any, ...]
    kwargs: SerializedData

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, CallbackTask):
            return NotImplemented

        return self.priority < other.priority
