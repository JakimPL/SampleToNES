from dataclasses import dataclass
from typing import Generic, List, TypeVar, Union

T = TypeVar("T")


@dataclass(frozen=True)
class RunCompleted(Generic[T]):
    """A run whose every task answered, with the answers in the order the tasks were given."""

    results: List[T]


@dataclass(frozen=True)
class RunCanceled:
    """A run withdrawn before every task answered."""


@dataclass(frozen=True)
class RunFailed:
    """A run ended by the exception a task or the building of the tasks raised."""

    exception: Exception


RunOutcome = Union[RunCompleted[T], RunCanceled, RunFailed]
