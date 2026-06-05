from __future__ import annotations

from abc import ABC
from typing import Callable, Generic, List, TypeVar

from sampletones_application.utils.callbacks.queue import CallbackQueue

T = TypeVar("T")


class ServiceBase(ABC, Generic[T]):
    def __init__(self, priority: int = 0) -> None:
        self._priority = priority
        self._listeners: List[Callable[[T], None]] = []

    def subscribe(self, handler: Callable[[T], None]) -> None:
        self._listeners.append(handler)

    def unsubscribe(self, handler: Callable[[T], None]) -> None:
        if handler in self._listeners:
            self._listeners.remove(handler)

    def _emit(self, result: T) -> None:
        for listener in self._listeners:
            CallbackQueue.add(listener, result, priority=self._priority)
