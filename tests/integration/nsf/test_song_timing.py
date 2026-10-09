from fractions import Fraction
from typing import Final

import pytest

from sampletones_core.timing import SONG_TICK_BOUNDS, Meter, RowRate, SongTiming
from sampletones_player.clock.schedule import PlaySchedule
from sampletones_player.specification.clock import NTSC_FRAME_RATE
from tests.suite.groove import bar_rows

COMMON_TIME: Final[Meter] = Meter(rows=16, first_highlight=4, second_highlight=16)
FRAMES: Final[int] = 100
HALF: Final[Fraction] = Fraction(1, 2)
CALL_SECONDS: Final[Fraction] = 1 / Fraction(NTSC_FRAME_RATE)


class TestABarLineReachesTheConsoleOnTime:
    """Rows are planned in engine ticks, and the console's call re-clocks the ticks onto its own rate.

    Each layer carries its own remainder, so a bar line the console plays lands within half a tick
    of its exact moment plus one call, at any engine rate and however long the song runs. The drift
    the driver's rounded step builds over the run is counted on top.
    """

    @pytest.mark.parametrize("nes_frequency", (15, 41, 60, 300))
    @pytest.mark.parametrize("tempo", (97, 125, 210, 251))
    def test_every_bar_line_lands_within_half_a_tick_and_one_call(self, nes_frequency: int, tempo: int) -> None:
        timing = SongTiming(
            rate=RowRate.from_parameters(tempo=tempo, speed=6, nes_frequency=nes_frequency),
            meter=COMMON_TIME,
            bounds=SONG_TICK_BOUNDS,
        )
        schedule = PlaySchedule.from_parameters(nes_frequency)
        calls = 0
        tick_seconds = 1 / Fraction(nes_frequency)
        drift = schedule.maximum_drift(int(timing.frame_tick(FRAMES) / schedule.ticks_per_play_call) + 1)
        allowed = (HALF + drift) * tick_seconds + CALL_SECONDS
        for row in bar_rows(COMMON_TIME, FRAMES):
            tick = timing.tick_at(*divmod(row, COMMON_TIME.rows))
            while schedule.ticks_at(calls + 1) < tick:
                calls += 1

            exact = row * timing.exact_row_ticks * tick_seconds
            assert abs(calls * CALL_SECONDS - exact) <= allowed
