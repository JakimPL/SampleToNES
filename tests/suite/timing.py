import gc
from time import process_time
from typing import Callable, Final, List, Tuple

REPEATS: Final[int] = 3
MINIMUM_READING: Final[float] = 0.25
FIRST_BATCH: Final[int] = 1
MOST_RUNS: Final[int] = 1 << 20


def seconds(work: Callable[[], object]) -> float:
    """What one run of the work costs, taken as the best of several batches.

    A process's own time is counted in steps: Linux counts it in nanoseconds, Windows in about a
    sixtieth of a second, so a run of a few milliseconds reads there as either nothing at all or
    as a whole step. The batch is therefore grown until it stands well clear of one step, and what
    comes back is the batch divided by the runs in it — a reading the coarsest clock can see.

    The collector is held off for the reading, since it runs on how much is live rather than on
    what the work does: a batch building ten times the objects meets it more often and reads as
    more than ten times the cost. What is left is how the work itself follows its input, and the
    collector is armed again once the reading comes back, on whatever the batches left behind.
    """
    collecting = gc.isenabled()
    gc.disable()
    try:
        runs, reached = _runs_reaching(work)
        readings: List[float] = [reached / runs]
        readings.extend(_batch(work, runs) / runs for _ in range(REPEATS - 1))
    finally:
        if collecting:
            gc.enable()

    return min(readings)


def _runs_reaching(work: Callable[[], object]) -> Tuple[int, float]:
    """The batch that costs more than the clock's own step, doubling until it does.

    The batch that qualified is a reading like any other, so it comes back beside the run count
    it took and stands as the first of the readings.
    """
    runs = FIRST_BATCH
    reading = _batch(work, runs)
    while runs < MOST_RUNS and reading < MINIMUM_READING:
        runs *= 2
        reading = _batch(work, runs)

    return runs, reading


def _batch(work: Callable[[], object], runs: int) -> float:
    """What a run of the work this many times over costs, as the process counts its own time."""
    started = process_time()
    for _ in range(runs):
        work()

    return process_time() - started
