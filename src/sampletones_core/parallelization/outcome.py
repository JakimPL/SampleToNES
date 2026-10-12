from dataclasses import dataclass
from typing import Generic, List, Tuple, TypeVar, Union

T = TypeVar("T")


@dataclass(frozen=True)
class TaskFailure:
    """A task that ended in an error while its run went on, named by its place among the tasks."""

    index: int
    exception: Exception


@dataclass(frozen=True)
class RunCompleted(Generic[T]):
    """A run whose every task was answered.

    ``results`` holds the answers in the order the tasks were given. A run that outlives a failing
    task holds that task in ``failures`` and leaves its answer out of ``results``.
    """

    results: List[T]
    failures: Tuple[TaskFailure, ...]


@dataclass(frozen=True)
class RunCanceled:
    """A run withdrawn before every task answered."""


@dataclass(frozen=True)
class RunFailed:
    """A run ended by the exception a task or the building of the tasks raised."""

    exception: Exception


RunOutcome = Union[RunCompleted[T], RunCanceled, RunFailed]
