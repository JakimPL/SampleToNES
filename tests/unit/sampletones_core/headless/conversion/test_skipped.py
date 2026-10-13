from pathlib import Path
from typing import Final

from pebble import ProcessExpired

from sampletones_core.constants.enums import DEFAULT_CHANNELS
from sampletones_core.headless.conversion.request import classic_setup
from sampletones_core.headless.conversion.skipped import skipped_lines
from sampletones_core.reconstructions.converter import ConversionJob, ConversionOutcome, SkippedJob
from tests.suite.base import BaseTestSuite

KICK: Final[Path] = Path("/samples/kick.wav")
SNARE: Final[Path] = Path("/samples/snare.wav")


def _skipped(source: Path, exception: Exception) -> SkippedJob:
    job = ConversionJob(
        sources=(source,),
        stems=classic_setup(DEFAULT_CHANNELS),
        output_path=source.with_suffix(".stn"),
    )
    return SkippedJob(job=job, exception=exception)


class TestWhatARunSaysAboutTheRecordingsItSkipped(BaseTestSuite):
    """A run that went on without some recordings counts them, then names each with its error."""

    def test_a_run_that_skipped_nothing_says_nothing(self) -> None:
        assert skipped_lines(ConversionOutcome(written=(KICK.with_suffix(".stn"),), skipped=())) == ()

    def test_each_skipped_recording_is_named_with_its_error(self) -> None:
        outcome = ConversionOutcome(
            written=(),
            skipped=(
                _skipped(KICK, ZeroDivisionError("float division by zero")),
                _skipped(SNARE, ProcessExpired("Abnormal termination")),
            ),
        )

        assert skipped_lines(outcome) == (
            "Skipped 2 recordings that failed:",
            f"  {KICK}: ZeroDivisionError: float division by zero",
            f"  {SNARE}: ProcessExpired: Abnormal termination",
        )

    def test_one_skipped_recording_is_counted_as_one(self) -> None:
        outcome = ConversionOutcome(written=(), skipped=(_skipped(KICK, ValueError("unreadable")),))

        assert skipped_lines(outcome)[0] == "Skipped 1 recording that failed:"
