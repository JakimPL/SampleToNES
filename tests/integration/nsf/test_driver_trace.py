from dataclasses import dataclass
from typing import Final

import pytest

from sampletones_core.project.voices.sample import Sample
from sampletones_player.builder import song_from_reconstruction
from sampletones_player.compression.scheme import CompressionScheme
from sampletones_player.driver.image import DriverImage
from sampletones_player.nsf.song import song_to_bytes
from sampletones_player.song import Song
from sampletones_player.specification.binary import WORD_SIZE
from sampletones_player.specification.nsf import PROGRAM_SIZE
from sampletones_player.specification.song import STEP_FRACTION_OFFSET, STEP_WHOLE_OFFSET
from sampletones_tools.player.trace.trace import RegisterTrace
from tests.integration.nsf.console.session import (
    TRAILING_CALLS,
    captured_trace,
    captured_trace_over,
    play_calls_covering,
    play_calls_reaching,
)
from tests.integration.nsf.header import sample_information
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    PLAYER_OCTAVE_UP_TIMER,
    PLAYER_REFERENCE_TIMER,
    PLAYER_SILENT_VOLUME,
    player_song,
    pulse_tick,
    resting_streams,
)

HALF_RATE: Final[int] = 30
DOUBLE_RATE: Final[int] = 120
NTSC_RATE: Final[int] = 60
FAST_RATE: Final[int] = 300
ROUNDS: Final[int] = 4
ABSENT_SONG_NAME: Final[str] = "absent"


@pytest.fixture
def trace(song: Song, sample: Sample) -> RegisterTrace:
    """Every APU write the assembled driver makes over a full run of the sample."""
    return captured_trace(song, sample_information(sample.name))


@pytest.fixture
def expected(song: Song) -> RegisterTrace:
    """The writes the model states a correct driver makes over that same run."""
    return RegisterTrace.from_song(song, play_calls_covering(song))


class TestTheDriverWritesWhatTheModelStates:
    """The assembled 6502 driver run on py65, held against `RegisterTrace.from_song`."""

    def test_initialization_readies_the_console_the_way_the_model_states(
        self,
        trace: RegisterTrace,
        expected: RegisterTrace,
    ) -> None:
        assert trace.initialization == expected.initialization

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
        song = song_from_reconstruction(reclocked, loop_tick=None, scheme=CompressionScheme.SEARCH)

        trace = captured_trace(song, sample_information(sample.name))
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
        reclocked_block = song_to_bytes(
            song_from_reconstruction(reclocked, loop_tick=None, scheme=CompressionScheme.SEARCH), available
        )

        assert block[STEP_FRACTION_OFFSET + WORD_SIZE :] == reclocked_block[STEP_FRACTION_OFFSET + WORD_SIZE :]
        assert block[:STEP_WHOLE_OFFSET] == reclocked_block[:STEP_WHOLE_OFFSET]


class TestARepeatingSongComesRoundWhereTheModelSaysItDoes(BaseTestSuite):
    """A song that repeats re-enters its streams partway through.

    What the driver restores at the loop is the byte each plane resumes at, which
    the header states, so a plane comes back holding nothing of the run that led up to it. The
    tick the loop returns to therefore starts a token of its own on every plane.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: int
        name: str
        nes_frequency: int
        remaining: int

        @property
        def label(self) -> str:
            return self.name

    test_cases = (
        TestCase(name="half-the-song", nes_frequency=NTSC_RATE, remaining=0, expected=ROUNDS),
        TestCase(name="one-tick-loop", nes_frequency=NTSC_RATE, remaining=1, expected=ROUNDS),
        TestCase(name="one-tick-loop-fast", nes_frequency=FAST_RATE, remaining=1, expected=ROUNDS),
        TestCase(name="half-the-song-fast", nes_frequency=FAST_RATE, remaining=0, expected=ROUNDS),
    )

    @staticmethod
    def repeating(sample: Sample, test_case: "TestCase") -> Song:
        reclocked = sample.reconstruction.with_nes_frequency(test_case.nes_frequency)
        ticks = song_from_reconstruction(reclocked, loop_tick=None, scheme=CompressionScheme.SEARCH).ticks
        loop_tick = ticks - test_case.remaining if test_case.remaining else ticks // 2
        return song_from_reconstruction(reclocked, loop_tick=loop_tick, scheme=CompressionScheme.SEARCH)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_driver_writes_what_the_model_states(
        self,
        test_case: TestCase,
        sample: Sample,
    ) -> None:
        song = self.repeating(sample, test_case)
        assert song.loop_tick is not None
        covered = song.ticks + test_case.expected * (song.ticks - song.loop_tick)
        calls = play_calls_reaching(song, covered)

        trace = captured_trace_over(song, sample_information(sample.name), calls)
        assert trace == RegisterTrace.from_song(song, calls)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_run_keeps_sounding_past_the_songs_end(
        self,
        test_case: TestCase,
        sample: Sample,
    ) -> None:
        """A song without a loop falls silent where it ends, and one with a loop plays on."""
        song = self.repeating(sample, test_case)
        assert song.loop_tick is not None
        covered = song.ticks + test_case.expected * (song.ticks - song.loop_tick)
        calls = play_calls_reaching(song, covered)

        trace = captured_trace_over(song, sample_information(sample.name), calls)
        assert any(writes for writes in trace.play_calls[-TRAILING_CALLS:])


class TestAPlaneTheBlockLeavesOut:
    """A plane holding zero throughout is absent: the header states a sentinel and the driver
    leaves it standing at zero, on the first pass and on every pass a loop brings round.
    """

    FIGURE: Final = (
        pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_REFERENCE_TIMER),
        pulse_tick(PLAYER_FULL_VOLUME, 1, PLAYER_OCTAVE_UP_TIMER),
        pulse_tick(PLAYER_SILENT_VOLUME, 1, PLAYER_OCTAVE_UP_TIMER),
    )
    LOOP_TICK: Final[int] = 1

    @pytest.fixture
    def unbent(self) -> Song:
        """A repeating song on one pulse channel, none of its tone channels bending."""
        return player_song(resting_streams(self.FIGURE * ROUNDS), NTSC_RATE, loop_tick=self.LOOP_TICK)

    def test_the_song_leaves_its_bend_planes_out(self, unbent: Song) -> None:
        streams = unbent.planes.streams
        assert not streams.pulse1_bend
        assert not streams.pulse2_bend
        assert not streams.triangle_bend

    def test_the_console_writes_what_the_model_states_across_its_loops(self, unbent: Song) -> None:
        calls = play_calls_reaching(unbent, ROUNDS * unbent.ticks)
        trace = captured_trace_over(unbent, sample_information(ABSENT_SONG_NAME), calls)
        assert trace == RegisterTrace.from_song(unbent, calls)
