from typing import Final, Optional

from sampletones_player.song import Song
from tests.suite.player import PLAYER_PITCHES, noise_tick, player_song, player_streams, pulse_tick, triangle_tick

DECK_SONG_TICKS: Final[int] = 240
LEVEL_COUNT: Final[int] = 16
DUTY_CYCLE_COUNT: Final[int] = 4
NOISE_MODE_COUNT: Final[int] = 2
NOISE_PERIOD_COUNT: Final[int] = 16
FIRST_PULSE_LOW: Final[int] = 24
FIRST_PULSE_SPAN: Final[int] = 36
SECOND_PULSE_LOW: Final[int] = 40
SECOND_PULSE_SPAN: Final[int] = 30
SECOND_PULSE_STRIDE: Final[int] = 5
SECOND_PULSE_LEVEL_STRIDE: Final[int] = 7
TRIANGLE_LOW: Final[int] = 20
TRIANGLE_SPAN: Final[int] = 40
TRIANGLE_STRIDE: Final[int] = 3
TRIANGLE_PHRASE: Final[int] = 7
TRIANGLE_REST_EVERY: Final[int] = 3
DUTY_HOLD: Final[int] = 16
SECOND_DUTY_HOLD: Final[int] = 5
NOISE_LEVEL_HOLD: Final[int] = 3
NOISE_MODE_HOLD: Final[int] = 11


def deck_song(nes_frequency: int, loop_tick: Optional[int]) -> Song:
    """A song turning every reading the screen shows over within a few seconds.

    Each channel walks through its levels, its pitches and its timbres at a pace of its own,
    the triangle rests every third phrase, and the noise turns its period every tick and its
    mode every few, so a paused screen meets every shape, note and meter the deck draws.

    Args:
        nes_frequency: The rate the streams are written at.
        loop_tick: The tick the song returns to once it ends, or ``None`` where it stops there.

    Returns:
        Song: The song, a few seconds long at the hardware rate.
    """
    ticks = range(DECK_SONG_TICKS)
    timers = PLAYER_PITCHES.timers
    streams = player_streams(
        pulse1=[
            pulse_tick(
                LEVEL_COUNT - 1 - tick % LEVEL_COUNT,
                (tick // DUTY_HOLD) % DUTY_CYCLE_COUNT,
                timers[FIRST_PULSE_LOW + tick % FIRST_PULSE_SPAN],
            )
            for tick in ticks
        ],
        pulse2=[
            pulse_tick(
                (tick * SECOND_PULSE_LEVEL_STRIDE) % LEVEL_COUNT,
                (tick // SECOND_DUTY_HOLD) % DUTY_CYCLE_COUNT,
                timers[SECOND_PULSE_LOW + (tick * SECOND_PULSE_STRIDE) % SECOND_PULSE_SPAN],
            )
            for tick in ticks
        ],
        triangle=[
            triangle_tick(
                (tick // TRIANGLE_PHRASE) % TRIANGLE_REST_EVERY != 0,
                timers[TRIANGLE_LOW + (tick * TRIANGLE_STRIDE) % TRIANGLE_SPAN],
            )
            for tick in ticks
        ],
        noise=[
            noise_tick(
                (tick // NOISE_LEVEL_HOLD) % LEVEL_COUNT,
                (tick // NOISE_MODE_HOLD) % NOISE_MODE_COUNT,
                tick % NOISE_PERIOD_COUNT,
            )
            for tick in ticks
        ],
    )
    return player_song(streams, nes_frequency, loop_tick=loop_tick)
