from abc import ABC
from dataclasses import dataclass
from typing import Callable, Generic, List, TypeVar

from sampletones_application.utils.callbacks.latest import LatestDelivery
from sampletones_application.utils.callbacks.queue import CallbackQueue

T = TypeVar("T")


@dataclass(frozen=True)
class _Subscription(Generic[T]):
    """One subscriber, and the delivery its reports wait in."""

    handler: Callable[[T], None]
    reports: LatestDelivery[[T]]


class ServiceBase(ABC, Generic[T]):
    """
    The boundary between synchronous application logic and asynchronous computation.

    Two properties follow from this design:

    - *Thread containment* — results are routed through ``CallbackQueue`` so
      the thread boundary is fully contained and callers treat results as
      ordinary synchronous values.
    - *Exhaustive result types* — result types form a tagged union; subscribers
      handle each case with ``match``, making incomplete handling a type error.

    A result travels one of two ways. ``_emit`` delivers every result it is given, which is how an
    outcome travels. ``_report`` carries where a run stands, and a report still waiting for the
    render thread is superseded by the next, so a subscriber draws the newest one once per drain.
    """

    def __init__(self, priority: int = 0) -> None:
        self._priority = priority
        self._subscriptions: List[_Subscription[T]] = []

    def subscribe(self, handler: Callable[[T], None]) -> None:
        self._subscriptions.append(
            _Subscription(
                handler=handler,
                reports=LatestDelivery(handler, priority=self._priority),
            )
        )

    def unsubscribe(self, handler: Callable[[T], None]) -> None:
        for subscription in self._subscriptions:
            if subscription.handler == handler:
                self._subscriptions.remove(subscription)
                return

    def _emit(self, result: T) -> None:
        for subscription in self._subscriptions:
            CallbackQueue.add(subscription.handler, result, priority=self._priority)

    def _report(self, result: T) -> None:
        for subscription in self._subscriptions:
            subscription.reports.post(result)

    @property
    def class_name(self) -> str:
        return self.__class__.__name__
