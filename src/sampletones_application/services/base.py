from __future__ import annotations

from abc import ABC
from typing import Callable, Generic, List, TypeVar

from sampletones_application.utils.callbacks.queue import CallbackQueue

T = TypeVar("T")


class ServiceBase(ABC, Generic[T]):
    """Abstract base for asynchronous background workers.

    Services wrap long-running core-library operations (file conversion,
    waveform regeneration, WAV/FTIS export) and deliver their results to the
    main thread safely.  They follow a subscriber pattern: interested parties
    call ``subscribe(handler)`` before the operation starts, and when the
    operation produces a result the service posts it to ``CallbackQueue`` rather
    than calling the handler directly.

    Responsibilities:
    - Manage a list of result handlers (``subscribe`` / ``unsubscribe``).
    - Emit typed result values to all subscribers via ``_emit``, which always
      routes through ``CallbackQueue`` at the configured priority.

    Governing principles:
    - Services do not import from ``ui/``, ``view_model/``, ``coordinators/``,
      or ``logic/``.
    - ``_emit`` must never call a handler directly from a background thread;
      all delivery goes through ``CallbackQueue.add``.
    - Result types form a tagged union (``ServiceStarted``, ``ServiceProgress``,
      ``ServiceSuccess``, ``ServiceError``, ``ServiceCancelled``, and optionally
      ``ServiceIntermediate``).  Subscribers use ``match`` to handle each case.

    Subclasses implement the actual async operation (``start``, ``cancel``,
    ``cleanup``) and call ``_emit`` from their internal callbacks.

    Dependencies: ``CallbackQueue``.
    """

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
