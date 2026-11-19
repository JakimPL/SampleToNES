from dataclasses import dataclass
from typing import Callable, Dict, Final, List, Optional, Tuple

import pytest

from sampletones_core.project.voices.sample import Sample
from sampletones_player.driver.image import DriverImage
from sampletones_player.information import ProgramInformation
from sampletones_player.nsf.file import nsf_to_bytes
from sampletones_player.song import Song
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
TracedSong = Tuple[Song, ProgramInformation]


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


class TestARestingTriangleWritesItsCounterAlone(BaseTestSuite):
    """A resting triangle writes its silenced counter alone, so its divider stays where it last sounded.

    These are the songs where a tick the stream sounded is never written: a call moving several
    ticks skips the last sounding one, or a loop comes round onto a rest while the bend plane
    starts over. The cartridge carries the very driver an NSF does, so both hold to the model there.
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
