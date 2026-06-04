from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

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
