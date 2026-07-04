from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Generic, Optional, TypeVar, Union

from sampletones_core.parallelization import TaskProgress

T = TypeVar("T")


@dataclass(frozen=True)
class ServiceStarted:
    total: int


@dataclass(frozen=True)
class ServiceProgress(Generic[T]):
    completed: int
    total: int
    current_item: Optional[T] = None
    eta_seconds: Optional[float] = None


@dataclass(frozen=True)
class ServiceSuccess(Generic[T]):
    value: T


@dataclass(frozen=True, eq=False)
class ServiceError:
    exception: Exception


@dataclass(frozen=True)
class ServiceCancelled:
    pass


@dataclass(frozen=True)
class ServiceIntermediate(Generic[T]):
    data: T


ConversionResult = Union[
    ServiceStarted,
    ServiceProgress[Path],
    ServiceIntermediate[TaskProgress],
    ServiceSuccess[Path],
    ServiceError,
    ServiceCancelled,
]
