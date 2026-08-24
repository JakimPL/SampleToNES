from dataclasses import dataclass
from typing import Final, Generic, Optional, TypeVar

T = TypeVar("T")

NOTHING_TO_DO: Final[int] = 0
NOTHING_UNDER_WAY: Final[float] = 0.0


@dataclass(frozen=True)
class ServiceStarted:
    total: int


@dataclass(frozen=True)
class ServiceProgress(Generic[T]):
    """How far an operation has come, in the items it is measured in.

    An operation whose items report their own progress states what the one under way has covered
    as ``partial``, so the run reads as a whole while the counts keep naming the items a reader
    recognizes.

    Attributes:
        completed: The items the operation has finished.
        total: The items the operation is measured against.
        current_item: What the operation is working on, as the operation names it.
        eta_seconds: How long the operation has left, where its rate says.
        partial: The work under way beyond ``completed``, counted in items.
    """

    completed: int
    total: int
    current_item: Optional[T] = None
    eta_seconds: Optional[float] = None
    partial: float = NOTHING_UNDER_WAY

    @property
    def fraction(self) -> float:
        """How full the operation stands, the item under way counted for the part of it done."""
        if self.total == NOTHING_TO_DO:
            return 0.0

        return (self.completed + self.partial) / self.total


@dataclass(frozen=True)
class ServiceSuccess(Generic[T]):
    value: T


@dataclass(frozen=True, eq=False)
class ServiceError:
    exception: Exception


@dataclass(frozen=True)
class ServiceCanceled:
    pass


@dataclass(frozen=True)
class ServiceIntermediate(Generic[T]):
    data: T
