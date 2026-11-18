from dataclasses import dataclass
from typing import Callable, Dict, Final, FrozenSet, List, Optional, Tuple

import pytest

from sampletones_core.project.voices.sample import Sample
from sampletones_player.driver.image import DriverImage
from sampletones_player.information import ProgramInformation
from sampletones_player.nsf.file import nsf_to_bytes
from sampletones_player.song import Song
from sampletones_player.specification.registers import (
    TRIANGLE_COUNTER_CONTROL,
    TRIANGLE_LINEAR_COUNTER,
    TRIANGLE_SILENT_RELOAD,
    TRIANGLE_TIMER_HIGH,
    TRIANGLE_TIMER_LOW,
)
from sampletones_tools.player.trace.trace import RegisterTrace
from tests.integration.nsf.console.session import captured_run
from tests.integration.nsf.header import sample_information
from tests.integration.rom.session import calls_through, cartridge_trace, reclocked_song
from tests.integration.rom.songs import DECK_SONG_TICKS, deck_song
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    PLAYER_OCTAVE_UP_TIMER,
    PLAYER_REFERENCE_TIMER,
    PLAYER_SILENT_VOLUME,
    player_song,
    pulse_tick,
    resting_streams,
)

NTSC_RATE: Final[int] = 60
HALF_RATE: Final[int] = 30
FAST_RATE: Final[int] = 300
FIGURE_REPEATS: Final[int] = 2
ABSENT_SONG_NAME: Final[str] = "absent"
DECK_INFORMATION: Final[ProgramInformation] = ProgramInformation(title="Deck", artist="Every reading")
DECK_LOOP_TICK: Final[int] = DECK_SONG_TICKS // 2
SILENT_LINEAR_COUNTER: Final[int] = TRIANGLE_COUNTER_CONTROL | TRIANGLE_SILENT_RELOAD
TRIANGLE_DIVIDER: Final[FrozenSet[int]] = frozenset({TRIANGLE_TIMER_LOW, TRIANGLE_TIMER_HIGH})
RESTING_TRIANGLE_DIVIDER: Final[str] = (
    "a resting triangle holds the divider of the last tick the driver wrote, and the model the one of the last "
    "tick the stream sounded, which part where a call skips that tick or a loop comes round onto a rest"
)

RegisterState = Dict[int, int]
TracedSong = Tuple[Song, ProgramInformation]


def register_states(trace: RegisterTrace) -> List[RegisterState]:
    """What every register holds once each play call of a trace has written, initialization included."""
    held: RegisterState = {write.address: write.value for write in trace.initialization}
    states: List[RegisterState] = []
    for writes in trace.play_calls:
        held.update({write.address: write.value for write in writes})
        states.append(dict(held))

    return states


def corpus_songs(catalog: Dict[str, Sample], nes_frequency: int, *, looping: bool) -> List[TracedSong]:
    """Every sample of the corpus built at ``nes_frequency``, each with the text it is listed under."""
    return [
        (reclocked_song(sample, nes_frequency, looping=looping), sample_information(sample.name))
        for sample in catalog.values()
    ]


class TestTheCartridgeSoundsWhatTheModelStates(BaseTestSuite):
    """The cartridge's boot stands where an NSF's initialization does and each frame where a play call does.

    The shell carries the same driver an NSF carries and calls it once a frame, so every rate a
    song is built at reaches the APU as the model of the driver states. The corpus's samples
    each sound a few of the channels, which leaves the planes of the others out.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        nes_frequency: int

    test_cases = (
        TestCase(label="60-hz", nes_frequency=NTSC_RATE),
        TestCase(label="30-hz", nes_frequency=HALF_RATE),
        TestCase(label="300-hz", nes_frequency=FAST_RATE),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_trace_equals_the_model_s(self, test_case: TestCase, instrument_catalog: Dict[str, Sample]) -> None:
        for song, information in corpus_songs(instrument_catalog, test_case.nes_frequency, looping=False):
            calls = calls_through(song)

            assert cartridge_trace(song, information, calls) == RegisterTrace.from_song(song, calls)


class TestEveryChannelSoundsWhatTheModelStates(BaseTestSuite):
    """A song sounding all four channels, every register and every change of phase among them, round its loop too."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        nes_frequency: int
        loop_tick: Optional[int]

    test_cases = (
        TestCase(label="60-hz", nes_frequency=NTSC_RATE, loop_tick=None),
        TestCase(label="60-hz-looping", nes_frequency=NTSC_RATE, loop_tick=DECK_LOOP_TICK),
        TestCase(label="30-hz-looping", nes_frequency=HALF_RATE, loop_tick=DECK_LOOP_TICK),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_trace_equals_the_model_s(self, test_case: TestCase) -> None:
        song = deck_song(test_case.nes_frequency, test_case.loop_tick)
        calls = calls_through(song)

        assert cartridge_trace(song, DECK_INFORMATION, calls) == RegisterTrace.from_song(song, calls)


class TestACartridgeOfAFewChannels:
    """A song sounding one pulse channel leaves every other plane out, and the cartridge holds them silent."""

    FIGURE: Final = (
        pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_REFERENCE_TIMER),
        pulse_tick(PLAYER_FULL_VOLUME, 1, PLAYER_OCTAVE_UP_TIMER),
        pulse_tick(PLAYER_SILENT_VOLUME, 1, PLAYER_OCTAVE_UP_TIMER),
    )
    LOOP_TICK: Final[int] = 1

    @pytest.fixture
    def sparse(self) -> Song:
        """A repeating song on one pulse channel, its other channels resting on one tick."""
        return player_song(resting_streams(self.FIGURE * FIGURE_REPEATS), NTSC_RATE, loop_tick=self.LOOP_TICK)

    def test_the_song_leaves_planes_out(self, sparse: Song) -> None:
        streams = sparse.planes.streams
        assert not streams.pulse2_control
        assert not streams.noise_control

    def test_the_trace_equals_the_model_s_across_its_loops(self, sparse: Song) -> None:
        calls = calls_through(sparse)

        trace = cartridge_trace(sparse, sample_information(ABSENT_SONG_NAME), calls)

        assert trace == RegisterTrace.from_song(sparse, calls)


class TestARestingTriangleHoldsADividerOfItsOwn(BaseTestSuite):
    """A resting triangle keeps its divider where it last sounded, and the driver and the model read that apart.

    The driver keeps the pitch of the last tick it wrote under the bend its bend plane holds, and
    the model the divider of the last tick the stream sounded before the rest. The two part where
    a call moving several ticks skips that tick, and where a loop comes round onto a rest, since
    the bend plane starts over at the loop while the pitch stays. The linear counter holds the
    channel silent through the rest, so the console sounds the same either way, and the next tick
    the triangle sounds on states its own divider in both. The cartridge carries the very driver
    an NSF does, so it parts with the model exactly where the NSF parts with it.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        songs: Callable[[Dict[str, Sample]], List[TracedSong]]

    test_cases = (
        TestCase(
            label="300-hz-four-channels",
            songs=lambda catalog: [
                (deck_song(FAST_RATE, loop_tick), DECK_INFORMATION) for loop_tick in (None, DECK_LOOP_TICK)
            ],
        ),
        TestCase(label="60-hz-looping-corpus", songs=lambda catalog: corpus_songs(catalog, NTSC_RATE, looping=True)),
        TestCase(label="30-hz-looping-corpus", songs=lambda catalog: corpus_songs(catalog, HALF_RATE, looping=True)),
        TestCase(label="300-hz-looping-corpus", songs=lambda catalog: corpus_songs(catalog, FAST_RATE, looping=True)),
    )

    @pytest.mark.xfail(strict=True, reason=RESTING_TRIANGLE_DIVIDER)
    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_trace_equals_the_model_s(self, test_case: TestCase, instrument_catalog: Dict[str, Sample]) -> None:
        for song, information in test_case.songs(instrument_catalog):
            calls = calls_through(song)

            assert cartridge_trace(song, information, calls) == RegisterTrace.from_song(song, calls)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_cartridge_sounds_what_the_nsf_sounds(
        self, test_case: TestCase, instrument_catalog: Dict[str, Sample], driver_image: DriverImage
    ) -> None:
        for song, information in test_case.songs(instrument_catalog):
            calls = calls_through(song)

            nsf = nsf_to_bytes(song, information, driver_image)
            assert cartridge_trace(song, information, calls) == captured_run(nsf, calls)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_two_part_on_a_silent_triangle_s_divider_alone(
        self, test_case: TestCase, instrument_catalog: Dict[str, Sample]
    ) -> None:
        for song, information in test_case.songs(instrument_catalog):
            calls = calls_through(song)
            played = register_states(cartridge_trace(song, information, calls))
            stated = register_states(RegisterTrace.from_song(song, calls))

            for held, expected in zip(played, stated, strict=True):
                parted = {
                    address for address in held.keys() | expected.keys() if held.get(address) != expected.get(address)
                }
                assert parted <= TRIANGLE_DIVIDER
                if parted:
                    assert held[TRIANGLE_LINEAR_COUNTER] == SILENT_LINEAR_COUNTER
