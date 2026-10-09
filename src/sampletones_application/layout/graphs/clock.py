from typing import Tuple

from pydantic import BaseModel


class ClockLayout(BaseModel, extra="forbid", frozen=True):
    """How a time axis names the moments along it.

    Attributes:
        steps_seconds: The distances between marks a clock divides evenly into, in order.
        tick_count: The marks a stretch is read with, which picks the step from the list.
    """

    steps_seconds: Tuple[float, ...]
    tick_count: int
