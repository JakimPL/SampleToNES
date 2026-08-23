from typing import Final

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
