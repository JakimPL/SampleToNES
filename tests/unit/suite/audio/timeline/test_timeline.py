from typing import Final

import numpy as np

from tests.suite.audio.ramp import ramp, ramp_indices
from tests.suite.audio.timeline import Closed, Opened, Timeline, Violation, ViolationKind, Written

THREAD: Final[str] = "CaseThread"
BLOCK: Final[int] = 8


def _opened(stream: int) -> Opened:
    return Opened(stream=stream, device=0, sample_rate=44100, frames_per_buffer=BLOCK, thread=THREAD)


def _closed(stream: int) -> Closed:
    return Closed(stream=stream, discarded=0, thread=THREAD)


class TestStreamsHeldOpen:
    """The timeline answers which streams stand open, and the most the device held at one moment."""

    def test_streams_one_after_another_never_stand_open_together(self) -> None:
        timeline = Timeline()
        for stream in range(3):
            timeline.record(_opened(stream))
            timeline.record(_closed(stream))

        assert timeline.most_streams_open() == 1
        assert timeline.open_streams() == set()

    def test_a_stream_opened_before_another_closed_counts_two(self) -> None:
        timeline = Timeline()
        timeline.record(_opened(0))
        timeline.record(_opened(1))
        timeline.record(_closed(0))

        assert timeline.most_streams_open() == 2
        assert timeline.open_streams() == {1}

    def test_streams_are_listed_in_the_order_they_opened(self) -> None:
        timeline = Timeline()
        for stream in (2, 0, 1):
            timeline.record(_opened(stream))

        assert list(timeline.streams()) == [2, 0, 1]


class TestWhatWasPlayed:
    """The timeline holds what each stream played, in the order it arrived."""

    def test_one_stream_reads_back_alone(self) -> None:
        timeline = Timeline()
        timeline.record(Written(stream=0, samples=ramp(BLOCK), thread=THREAD))
        timeline.record(Written(stream=1, samples=ramp(BLOCK, start=100), thread=THREAD))
        timeline.record(Written(stream=0, samples=ramp(BLOCK, start=BLOCK), thread=THREAD))

        np.testing.assert_array_equal(ramp_indices(timeline.written(0)), np.arange(2 * BLOCK))

    def test_nothing_played_reads_as_no_samples(self) -> None:
        assert Timeline().written().size == 0

    def test_only_samples_carrying_sound_count_as_sounding(self) -> None:
        timeline = Timeline()
        timeline.record(Written(stream=0, samples=np.zeros(BLOCK, dtype=np.float32), thread=THREAD))
        timeline.record(Written(stream=0, samples=ramp(BLOCK, start=1), thread=THREAD))

        assert timeline.sounding_samples() == BLOCK


class TestViolations:
    """Every use of the device no correct playback makes is listed in the order it happened."""

    def test_violations_are_listed_in_order(self) -> None:
        timeline = Timeline()
        timeline.record(Violation(kind=ViolationKind.CLOSE_TWICE, stream=0, thread=THREAD))
        timeline.record(_opened(1))
        timeline.record(Violation(kind=ViolationKind.WRITE_AFTER_CLOSE, stream=1, thread=THREAD))

        assert timeline.violations() == [ViolationKind.CLOSE_TWICE, ViolationKind.WRITE_AFTER_CLOSE]

    def test_a_clean_timeline_lists_none(self) -> None:
        timeline = Timeline()
        timeline.record(_opened(0))
        timeline.record(_closed(0))

        assert timeline.violations() == []
