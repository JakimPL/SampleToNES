from typing import Final, Optional

PROGRESS_STEPS: Final[int] = 200


def silent_reporter(progress: object) -> bool:  # pylint: disable=unused-argument
    """Answers that the run goes on, which is what a caller watching nothing asks of it.

    A run reports through a reporter that answers whether its answer is still wanted, so a caller
    with nothing to watch supplies this one and hears the run through to its end. The report is
    taken as it comes, since a caller that reads none of it holds no opinion on its shape.
    """
    return True


def report_interval(total: int) -> int:
    """How far a count travels between two reports of a stage measured against ``total``.

    A stage may step through millions of samples or a handful of files, so reporting every step
    fills a queue with updates no eye resolves and no bar redraws. Spacing the reports over a
    fixed number of steps holds the rate steady whatever the stage counts in.

    Args:
        total: What the stage's count is measured against.

    Returns:
        int: The count a stage covers between reports, which is at least one.
    """
    return max(1, total // PROGRESS_STEPS)


class ReportRate:
    """How often a stage measured against a total is worth saying something about.

    What a stage counts moves by its own rules: a render's samples rise toward the song's length,
    while a compression's bytes fall as the dictionary earns its keep. A step is therefore a change
    of either sign, and a stage landing exactly on its total is always due, so a reading arrives at
    the end of every stage however it travelled there.

    The first reading a stage offers is due whatever it says, since a stage announcing where it
    begins is news to whoever is watching for it.
    """

    def __init__(self, total: int) -> None:
        """Holds the spacing a stage measured against ``total`` is reported at."""
        self._total = total
        self._interval = report_interval(total)
        self._reported: Optional[int] = None

    def take(self, completed: int) -> bool:
        """Takes ``completed`` as the reading to report, and answers whether it is due.

        A reading it takes is what the next one is measured from, so a stage moving in small steps
        is reported at the spacing this holds rather than at every step it makes.

        Args:
            completed: What the stage has covered so far, in the unit the stage counts in.

        Returns:
            bool: Whether the stage has moved far enough to be worth reporting.
        """
        if self._reported is not None and completed != self._total and abs(completed - self._reported) < self._interval:
            return False

        self._reported = completed
        return True
