from typing import Final

import pytest

from sampletones_player.information import ProgramInformation
from sampletones_player.rom.clock import ProgramClock
from sampletones_player.rom.program import SCREEN_TEXT
from sampletones_player.song import Song
from sampletones_player.specification.program import TITLE_COLUMNS
from sampletones_tools.player.graphics.deck.deck import Deck
from sampletones_tools.player.graphics.deck.state import NoiseState, PulseState, Transport, TriangleState
from sampletones_tools.player.trace.clock import CartridgeClock
from sampletones_tools.player.trace.screen import ScreenTrace
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    PLAYER_PITCHES,
    PLAYER_SILENT_VOLUME,
    noise_tick,
    player_song,
    player_streams,
    pulse_tick,
    triangle_tick,
)

NTSC_FREQUENCY: Final[int] = 60
LOW_PITCH: Final[int] = 30
HIGH_PITCH: Final[int] = 54
TRIANGLE_PITCH: Final[int] = 41
HALF_VOLUME: Final[int] = 7
WIDE_DUTY: Final[int] = 2
NARROW_DUTY: Final[int] = 0
LONG_MODE: Final[int] = 0
SHORT_MODE: Final[int] = 1
NOISE_PERIOD: Final[int] = 11
SECOND_NOISE_PERIOD: Final[int] = 3
LONG_TITLE: Final[str] = "Ćma " * TITLE_COLUMNS
INFORMATION: Final[ProgramInformation] = ProgramInformation(title=LONG_TITLE, artist="Author")
TICKS: Final[int] = 3


@pytest.fixture(name="song", scope="module")
def song_fixture() -> Song:
    """A song of three ticks, each channel changing what it sounds between them."""
    timers = PLAYER_PITCHES.timers
    return player_song(
        player_streams(
            pulse1=(
                pulse_tick(PLAYER_FULL_VOLUME, WIDE_DUTY, timers[LOW_PITCH]),
                pulse_tick(HALF_VOLUME, NARROW_DUTY, timers[HIGH_PITCH]),
                pulse_tick(PLAYER_SILENT_VOLUME, NARROW_DUTY, timers[HIGH_PITCH]),
            ),
            pulse2=(pulse_tick(HALF_VOLUME, NARROW_DUTY, timers[HIGH_PITCH]),) * TICKS,
            triangle=(
                triangle_tick(True, timers[TRIANGLE_PITCH]),
                triangle_tick(False, timers[TRIANGLE_PITCH]),
                triangle_tick(True, timers[TRIANGLE_PITCH]),
            ),
            noise=(
                noise_tick(PLAYER_FULL_VOLUME, LONG_MODE, NOISE_PERIOD),
                noise_tick(HALF_VOLUME, SHORT_MODE, SECOND_NOISE_PERIOD),
                noise_tick(PLAYER_SILENT_VOLUME, SHORT_MODE, SECOND_NOISE_PERIOD),
            ),
        ),
        NTSC_FREQUENCY,
        loop_tick=None,
    )


@pytest.fixture(name="deck", scope="module")
def deck_fixture() -> Deck:
    return Deck.load()


@pytest.fixture(name="screen_trace", scope="module")
def screen_trace_fixture(song: Song, deck: Deck) -> ScreenTrace:
    return ScreenTrace(song, INFORMATION, deck)


def frames_reaching(song: Song, tick: int) -> int:
    """The played frames after which the driver stands on ``tick``."""
    played = 1
    while song.tick_at(played - 1) != tick:
        played += 1

    return played


class TestTheChannelsShowTheTickTheDriverStandsOn:
    def test_before_any_frame_the_first_tick_shows(self, screen_trace: ScreenTrace) -> None:
        state = screen_trace.state_paused_after(0)

        assert state.pulse1 == PulseState(duty=WIDE_DUTY, level=PLAYER_FULL_VOLUME, pitch=LOW_PITCH)
        assert state.triangle == TriangleState(sounding=True, pitch=TRIANGLE_PITCH)
        assert state.noise == NoiseState(level=PLAYER_FULL_VOLUME, period=NOISE_PERIOD, short=False)

    def test_a_frame_shows_the_tick_it_left_the_driver_on(self, screen_trace: ScreenTrace, song: Song) -> None:
        state = screen_trace.state_paused_after(frames_reaching(song, 1))

        assert state.pulse1 == PulseState(duty=NARROW_DUTY, level=HALF_VOLUME, pitch=HIGH_PITCH)
        assert state.pulse2 == PulseState(duty=NARROW_DUTY, level=HALF_VOLUME, pitch=HIGH_PITCH)
        assert state.noise == NoiseState(level=HALF_VOLUME, period=SECOND_NOISE_PERIOD, short=True)

    def test_a_resting_triangle_shows_its_rest(self, screen_trace: ScreenTrace, song: Song) -> None:
        state = screen_trace.state_paused_after(frames_reaching(song, 1))

        assert not state.triangle.sounding

    def test_a_song_that_has_ended_holds_its_final_tick(self, screen_trace: ScreenTrace, song: Song) -> None:
        ended = screen_trace.state_paused_after(ProgramClock.of(song).total_frames + TICKS)
        final = screen_trace.state_paused_after(frames_reaching(song, TICKS - 1))

        assert (ended.pulse1, ended.pulse2, ended.triangle, ended.noise) == (
            final.pulse1,
            final.pulse2,
            final.triangle,
            final.noise,
        )


class TestTheTransportAndTheClock:
    def test_a_song_still_playing_shows_its_pause(self, screen_trace: ScreenTrace) -> None:
        assert screen_trace.state_paused_after(1).transport is Transport.PAUSED

    def test_a_song_that_has_ended_shows_its_stop(self, screen_trace: ScreenTrace, song: Song) -> None:
        ended = ProgramClock.of(song).total_frames

        assert screen_trace.state_paused_after(ended).transport is Transport.STOPPED

    def test_the_clock_stands_where_the_cartridge_counts_it(self, screen_trace: ScreenTrace, song: Song) -> None:
        program = ProgramClock.of(song)
        clock = CartridgeClock.after(program, TICKS)
        state = screen_trace.state_paused_after(TICKS)

        assert (state.played_seconds, state.progress, state.shimmer) == (
            clock.seconds,
            clock.progress_pixels,
            clock.shimmer,
        )
        assert state.total_seconds == ProgramClock.seconds_at(program.total_frames)


class TestTheTextIsTheOneTheScreenHasRoomFor:
    def test_each_line_is_fitted_to_its_field(self, screen_trace: ScreenTrace) -> None:
        state = screen_trace.state_paused_after(1)
        shown = INFORMATION.fitted(SCREEN_TEXT)

        assert (state.title, state.artist, state.copyright) == (shown.title, shown.artist, shown.copyright)
        assert len(state.title) == TITLE_COLUMNS
        assert state.title.startswith("Cma ")


class TestThePicture:
    def test_the_picture_is_the_deck_s_drawing_of_the_state(self, screen_trace: ScreenTrace, deck: Deck) -> None:
        assert screen_trace.paused_after(TICKS) == deck.showing(screen_trace.state_paused_after(TICKS))

    def test_a_negative_count_of_frames_is_refused(self, screen_trace: ScreenTrace) -> None:
        with pytest.raises(ValueError):
            screen_trace.paused_after(-1)
