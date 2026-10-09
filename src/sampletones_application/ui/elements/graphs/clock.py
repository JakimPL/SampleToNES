from math import floor
from typing import List, Tuple

from sampletones_application.layout.graphs.clock import ClockLayout
from sampletones_shared.utils.time import format_clock

ClockTick = Tuple[str, float]


def clock_step(span_seconds: float, layout: ClockLayout) -> float:
    """The distance between marks a stretch of time is read at.

    The steps a clock divides evenly into keep every mark a reading a listener already knows,
    and the smallest one leaving a readable handful of marks across the stretch is the one
    taken.

    Args:
        span_seconds: How much time the view covers.
        layout: The steps on offer and the marks a stretch is read with.

    Returns:
        float: The seconds one mark stands from the next.
    """
    rough = span_seconds / layout.tick_count
    return next((step for step in layout.steps_seconds if step >= rough), layout.steps_seconds[-1])


def clock_decimals(step_seconds: float) -> int:
    """How finely a reading divides a second, so that two neighboring marks read apart.

    Args:
        step_seconds: The seconds one mark stands from the next.

    Returns:
        int: The digits the fraction of a second is stated to.
    """
    if step_seconds >= 1.0:
        return 0
    if step_seconds >= 0.1:
        return 1

    return 2


def clock_ticks(
    start_seconds: float,
    end_seconds: float,
    rate: float,
    layout: ClockLayout,
) -> List[ClockTick]:
    """The marks a stretch of time is drawn with, each under the moment it stands at.

    A mark sits at a whole multiple of the step, so panning slides the same marks along rather
    than renaming them, and the label states the moment as a clock reading at the precision the
    step calls for.

    Args:
        start_seconds: Where the view begins.
        end_seconds: Where the view ends.
        rate: The positions one second holds, which the marks are placed in.
        layout: The steps on offer and the marks a stretch is read with.

    Returns:
        List[ClockTick]: Each mark's label beside the position it is drawn at.
    """
    if end_seconds <= start_seconds or rate <= 0.0:
        return []

    step = clock_step(end_seconds - start_seconds, layout)
    decimals = clock_decimals(step)
    first = floor(max(0.0, start_seconds) / step)
    last = floor(end_seconds / step)

    return [
        (format_clock(index * step, decimals), index * step * rate)
        for index in range(first, last + 1)
        if index * step >= start_seconds
    ]
