from dataclasses import dataclass
from typing import Callable

from sampletones_shared.exceptions import OperationCanceled


@dataclass(frozen=True)
class WalkProgress:
    """How far a walk through a song's order has sounded it.

    Attributes:
        ticks: The engine ticks every channel has sounded so far.
        total: The engine ticks the whole order lasts, which the project's groove states before
            a single row is played.
    """

    ticks: int
    total: int


WalkReporter = Callable[[WalkProgress], bool]


def announce(report: WalkReporter, ticks: int, total: int) -> None:
    """Tells a reporter how far the walk has come, and unwinds a walk it withdraws.

    Args:
        report: Hears the walk and answers whether it goes on.
        ticks: The engine ticks sounded so far.
        total: The engine ticks the whole order lasts.

    Raises:
        OperationCanceled: If the walk is no longer wanted.
    """
    if not report(WalkProgress(ticks=ticks, total=total)):
        raise OperationCanceled(f"the walk was withdrawn having sounded {ticks} of {total} ticks")
