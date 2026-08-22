from typing import Final

import pytest

from sampletones_player.compression.progress.monitor import CodecMonitor
from sampletones_player.compression.progress.report import (
    SILENT_REPORTER,
    CodecProgress,
)
from sampletones_shared.exceptions import OperationCancelled
from tests.suite.progress import FIRST_REPORT, RecordingReporter

PHRASES_FOUND: Final[int] = 4
BYTES_LAID_DOWN: Final[int] = 812
NOTHING: Final[int] = 0


class TestWhatARunSaysAboutItself:
    """The monitor carries the codec's own reckoning out to whoever asked for the run."""

    def test_a_reading_of_the_whole_song_reaches_the_caller(self) -> None:
        reporter: RecordingReporter[CodecProgress] = RecordingReporter()
        CodecMonitor(reporter).reached(PHRASES_FOUND, BYTES_LAID_DOWN)
        assert reporter.last == CodecProgress(phrases=PHRASES_FOUND, size=BYTES_LAID_DOWN)

    def test_a_run_that_has_read_nothing_yet_says_so(self) -> None:
        reporter: RecordingReporter[CodecProgress] = RecordingReporter()
        CodecMonitor(reporter).poll()
        assert reporter.last == CodecProgress(phrases=NOTHING, size=NOTHING)

    def test_a_stretch_between_readings_repeats_the_last_one(self) -> None:
        """Reading a plane says nothing new about the song, and still has to be heard."""
        reporter: RecordingReporter[CodecProgress] = RecordingReporter()
        monitor = CodecMonitor(reporter)
        monitor.reached(PHRASES_FOUND, BYTES_LAID_DOWN)
        monitor.poll()
        assert reporter.last == CodecProgress(phrases=PHRASES_FOUND, size=BYTES_LAID_DOWN)

    def test_what_the_run_last_reached_is_its_own_to_read(self) -> None:
        monitor = CodecMonitor(SILENT_REPORTER)
        monitor.reached(PHRASES_FOUND, BYTES_LAID_DOWN)
        assert monitor.progress == CodecProgress(phrases=PHRASES_FOUND, size=BYTES_LAID_DOWN)


class TestWithdrawingARun:
    """A caller that stops wanting the compression stops the compression."""

    def test_a_withdrawn_reading_unwinds_the_run(self) -> None:
        reporter: RecordingReporter[CodecProgress] = RecordingReporter(withdraw_at=FIRST_REPORT)
        with pytest.raises(OperationCancelled):
            CodecMonitor(reporter).reached(PHRASES_FOUND, BYTES_LAID_DOWN)

    def test_a_withdrawn_poll_unwinds_the_run(self) -> None:
        reporter: RecordingReporter[CodecProgress] = RecordingReporter(withdraw_at=FIRST_REPORT)
        with pytest.raises(OperationCancelled):
            CodecMonitor(reporter).poll()

    def test_a_withdrawal_names_what_the_run_was_holding(self) -> None:
        reporter: RecordingReporter[CodecProgress] = RecordingReporter(withdraw_at=FIRST_REPORT)
        with pytest.raises(OperationCancelled, match=str(BYTES_LAID_DOWN)):
            CodecMonitor(reporter).reached(PHRASES_FOUND, BYTES_LAID_DOWN)
