from time import process_time
from timeit import Timer
from typing import Callable, Final, List

REPEATS: Final[int] = 3


def seconds(work: Callable[[], object]) -> float:
    """What one run of the work costs, taken as the best of several batches.

    A process's own time is counted in steps: Linux counts it in nanoseconds, Windows in about a
    sixtieth of a second, so a run of a few milliseconds reads there as either nothing at all or
    as a whole step. ``Timer.autorange`` grows a batch until it stands well clear of one step, and
    what comes back is the batch divided by the runs in it — a reading the coarsest clock can see.

    The collector is held off for each batch, since it runs on how much is live rather than on
    what the work does: a batch building ten times the objects meets it more often and reads as
    more than ten times the cost. What is left is how the work itself follows its input.
    """
    timer = Timer(work, timer=process_time)
    runs, reached = timer.autorange()
    readings: List[float] = [reached / runs]
    readings.extend(reading / runs for reading in timer.repeat(REPEATS - 1, runs))
    return min(readings)
