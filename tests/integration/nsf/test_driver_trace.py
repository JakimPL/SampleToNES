from dataclasses import dataclass
from typing import Final

import pytest

from sampletones_core.project.instruments.sample import Sample
from sampletones_player.builder import song_from_reconstruction
from sampletones_player.driver.image import DriverImage
from sampletones_player.nsf.song import song_to_bytes
from sampletones_player.song import Song
from sampletones_player.specification.binary import WORD_SIZE
from sampletones_player.specification.nsf import PROGRAM_SIZE
from sampletones_player.specification.song import STEP_FRACTION_OFFSET, STEP_WHOLE_OFFSET
from sampletones_player.trace.trace import RegisterTrace
from tests.integration.nsf.console.session import (
    TRAILING_CALLS,
    captured_trace,
    play_calls_covering,
)
from tests.integration.nsf.exports import exported_information
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase

HALF_RATE: Final[int] = 30
DOUBLE_RATE: Final[int] = 120


@pytest.fixture
def trace(song: Song, sample: Sample) -> RegisterTrace:
    """Every APU write the assembled driver makes over a full run of the sample."""
    return captured_trace(song, exported_information(sample.name))


@pytest.fixture
def expected(song: Song) -> RegisterTrace:
    """The writes the model states a correct driver makes over that same run."""
    return RegisterTrace.from_song(song, play_calls_covering(song))


class TestTheDriverWritesWhatTheModelStates:
    """The assembled 6502 driver run on py65, held against `RegisterTrace.from_song`."""

    def test_initialisation_readies_the_console_the_way_the_model_states(
        self,
        trace: RegisterTrace,
        expected: RegisterTrace,
    ) -> None:
        assert trace.initialisation == expected.initialisation

    def test_every_play_call_writes_what_the_model_states(
        self,
        trace: RegisterTrace,
        expected: RegisterTrace,
    ) -> None:
        assert trace.play_calls == expected.play_calls

    def test_a_song_without_a_loop_stops_where_it_ends(self, trace: RegisterTrace) -> None:
        assert all(not writes for writes in trace.play_calls[-TRAILING_CALLS:])

    def test_the_run_sounds_every_tick_the_song_covers(
        self,
        trace: RegisterTrace,
        song: Song,
    ) -> None:
        sounding = [writes for writes in trace.play_calls if writes]
        assert len(sounding) + 1 == song.ticks


class TestAReClockedStreamPlaysTheSameTicks(BaseTestSuite):
    """A reconstruction built at another rate reaches the console through the same data.

    The file states one stream and the rate it was built at, and the driver advances that stream
    by a fractional number of ticks each call. Every rate therefore plays the same ticks in the
    same order, spread over as many calls as the rate asks for.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: int

        @property
        def label(self) -> str:
            return f"{self.expected} Hz"

    test_cases = (
        TestCase(expected=HALF_RATE),
        TestCase(expected=DOUBLE_RATE),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_driver_writes_what_the_model_states(
        self,
        test_case: TestCase,
        sample: Sample,
    ) -> None:
        reclocked = sample.reconstruction.with_nes_frequency(test_case.expected)
        song = song_from_reconstruction(reclocked, loop_tick=None)

        trace = captured_trace(song, exported_information(sample.name))
        assert trace == RegisterTrace.from_song(song, play_calls_covering(song))

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_rate_reaches_the_console_as_the_step_alone(
        self,
        test_case: TestCase,
        song: Song,
        sample: Sample,
        driver_image: DriverImage,
    ) -> None:
        reclocked = sample.reconstruction.with_nes_frequency(test_case.expected)
        available = PROGRAM_SIZE - len(driver_image.code)

        block = song_to_bytes(song, available)
        reclocked_block = song_to_bytes(song_from_reconstruction(reclocked, loop_tick=None), available)

        assert block[STEP_FRACTION_OFFSET + WORD_SIZE :] == reclocked_block[STEP_FRACTION_OFFSET + WORD_SIZE :]
        assert block[:STEP_WHOLE_OFFSET] == reclocked_block[:STEP_WHOLE_OFFSET]
