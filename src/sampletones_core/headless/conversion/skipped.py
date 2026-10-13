from typing import Final, Tuple

from sampletones_core.reconstructions.converter import ConversionOutcome, SkippedJob

ONE_RECORDING: Final[int] = 1


def skipped_lines(outcome: ConversionOutcome) -> Tuple[str, ...]:
    """What a finished run says about the recordings it went on without: a count, then one line apiece.

    A run that skipped nothing says nothing.
    """
    if not outcome.skipped:
        return ()

    count = len(outcome.skipped)
    noun = "recording" if count == ONE_RECORDING else "recordings"
    return (f"Skipped {count} {noun} that failed:", *(describe_skipped(skipped) for skipped in outcome.skipped))


def describe_skipped(skipped: SkippedJob) -> str:
    """One skipped job: the recordings it read and the error that ended it."""
    sources = ", ".join(str(source) for source in skipped.job.sources)
    exception = skipped.exception
    return f"  {sources}: {type(exception).__name__}: {exception}"
