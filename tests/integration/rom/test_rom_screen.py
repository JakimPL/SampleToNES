from dataclasses import dataclass
from typing import Callable, Dict, Final, Optional, Tuple

import pytest

from sampletones_core.project.voices.sample import Sample
from sampletones_player.information import ProgramInformation
from sampletones_player.rom.clock import ProgramClock
from sampletones_player.song import Song
from sampletones_tools.player.graphics.deck.deck import Deck
from sampletones_tools.player.trace.screen import ScreenTrace
from tests.integration.nsf.header import sample_information
from tests.integration.rom.session import SETTLING_FRAMES, paused_screen, reclocked_song
from tests.integration.rom.songs import DECK_SONG_TICKS, deck_song
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

NTSC_RATE: Final[int] = 60
HALF_RATE: Final[int] = 30
FAST_RATE: Final[int] = 300
DECK_LOOP_TICK: Final[int] = DECK_SONG_TICKS // 2
DECK_INFORMATION: Final[ProgramInformation] = ProgramInformation(title="Deck", artist="Every reading")
FOLDED_TITLE: Final[str] = "Żółw"
SPELLED_TITLE: Final[str] = "Zolw"
FOLDED_POINT: Final[int] = 5
FIRST_FRAME: Final[int] = 1
SECOND_FRAME: Final[int] = 2
SHIMMER_TURN: Final[int] = 4
HELD_FRAME: Final[int] = 5

PlayedPoint = Callable[[ProgramClock], int]
CATALOG_POINTS: Final[Tuple[PlayedPoint, ...]] = (
    lambda clock: FIRST_FRAME,
    lambda clock: clock.total_frames // 2,
    lambda clock: clock.total_frames - 1,
    lambda clock: clock.total_frames + SETTLING_FRAMES,
)


class TestThePausedScreenIsTheOneTheDeckStates(BaseTestSuite):
    """A paused cartridge holds one frame of the song on screen: its tick, its time and its progress.

    Each point lands somewhere the shell's arithmetic has a say: the first frames, the noise shape
    turning, a frame a slow song holds its tick through, seconds counted past the first, the last
    frame before the end, a song that has come round its loop, and one that has ended and holds
    its final tick. The song turns every reading over within a few seconds, so each point shows
    shapes, notes and meters of its own on all four channels.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        nes_frequency: int
        loop_tick: Optional[int]
        played: PlayedPoint

    test_cases = (
        TestCase(label="60-hz-first-frame", nes_frequency=NTSC_RATE, loop_tick=None, played=lambda clock: FIRST_FRAME),
        TestCase(
            label="60-hz-second-frame", nes_frequency=NTSC_RATE, loop_tick=None, played=lambda clock: SECOND_FRAME
        ),
        TestCase(
            label="60-hz-noise-shape-turned", nes_frequency=NTSC_RATE, loop_tick=None, played=lambda clock: SHIMMER_TURN
        ),
        TestCase(
            label="60-hz-a-third-in",
            nes_frequency=NTSC_RATE,
            loop_tick=None,
            played=lambda clock: clock.total_frames // 3,
        ),
        TestCase(
            label="60-hz-the-last-frame",
            nes_frequency=NTSC_RATE,
            loop_tick=None,
            played=lambda clock: clock.total_frames - 1,
        ),
        TestCase(
            label="60-hz-ended",
            nes_frequency=NTSC_RATE,
            loop_tick=None,
            played=lambda clock: clock.total_frames + SETTLING_FRAMES,
        ),
        TestCase(
            label="60-hz-come-round",
            nes_frequency=NTSC_RATE,
            loop_tick=DECK_LOOP_TICK,
            played=lambda clock: clock.total_frames + clock.loop_frames // 2,
        ),
        TestCase(label="30-hz-first-frame", nes_frequency=HALF_RATE, loop_tick=None, played=lambda clock: FIRST_FRAME),
        TestCase(label="30-hz-a-held-frame", nes_frequency=HALF_RATE, loop_tick=None, played=lambda clock: HELD_FRAME),
        TestCase(
            label="30-hz-halfway",
            nes_frequency=HALF_RATE,
            loop_tick=None,
            played=lambda clock: clock.total_frames // 2 + 1,
        ),
        TestCase(
            label="30-hz-come-round",
            nes_frequency=HALF_RATE,
            loop_tick=DECK_LOOP_TICK,
            played=lambda clock: clock.total_frames + clock.loop_frames - 1,
        ),
        TestCase(
            label="300-hz-halfway",
            nes_frequency=FAST_RATE,
            loop_tick=None,
            played=lambda clock: clock.total_frames // 2,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_screen_equals_the_trace(self, test_case: TestCase, deck: Deck) -> None:
        song = deck_song(test_case.nes_frequency, test_case.loop_tick)
        played = test_case.played(ProgramClock.of(song))

        expected = ScreenTrace(song, DECK_INFORMATION, deck).paused_after(played)

        assert paused_screen(song, DECK_INFORMATION, played) == expected


class TestEverySampleShowsWhatTheDeckStates(BaseTestSuite):
    """Every sample of the corpus shows its readings as the deck states them, at each rate and round a loop."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        nes_frequency: int
        looping: bool

    test_cases = (
        TestCase(label="60-hz", nes_frequency=NTSC_RATE, looping=False),
        TestCase(label="60-hz-looping", nes_frequency=NTSC_RATE, looping=True),
        TestCase(label="30-hz", nes_frequency=HALF_RATE, looping=False),
        TestCase(label="300-hz-looping", nes_frequency=FAST_RATE, looping=True),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_screen_equals_the_trace(
        self, test_case: TestCase, instrument_catalog: Dict[str, Sample], deck: Deck
    ) -> None:
        for sample in instrument_catalog.values():
            song = reclocked_song(sample, test_case.nes_frequency, looping=test_case.looping)
            information = sample_information(sample.name)
            trace = ScreenTrace(song, information, deck)
            clock = ProgramClock.of(song)
            for point in CATALOG_POINTS:
                played = point(clock)

                assert paused_screen(song, information, played) == trace.paused_after(played)


class TestATitleWithFoldedLetters:
    """The screen's font draws plain ASCII, so a title's accented letters show as the letters they are built on."""

    def test_the_title_reads_as_its_plain_letters(self, song: Song, deck: Deck) -> None:
        folded = ProgramInformation(title=FOLDED_TITLE, artist=SPELLED_TITLE)
        spelled = ProgramInformation(title=SPELLED_TITLE, artist=SPELLED_TITLE)

        expected = ScreenTrace(song, spelled, deck).paused_after(FOLDED_POINT)

        assert ScreenTrace(song, folded, deck).state_paused_after(FOLDED_POINT).title == SPELLED_TITLE
        assert paused_screen(song, folded, FOLDED_POINT) == expected
