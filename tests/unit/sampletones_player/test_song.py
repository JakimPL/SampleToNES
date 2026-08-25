from dataclasses import dataclass
from typing import Final, Optional, Tuple

import pytest
from pydantic import ValidationError

from sampletones_player.song import Song
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

NTSC_FREQUENCY: Final[int] = 60
SOUNDING: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_REFERENCE_TIMER)
RESTING: Final = pulse_tick(PLAYER_SILENT_VOLUME, 0, PLAYER_REFERENCE_TIMER)
OCTAVE_UP: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_OCTAVE_UP_TIMER)


class TestSongLoopBounds:
    """A loop point names a tick the song actually plays."""

    def test_a_loop_within_the_song_is_accepted(self) -> None:
        song = player_song(resting_streams((SOUNDING, OCTAVE_UP)), NTSC_FREQUENCY, loop_tick=1)
        assert song.loop_tick == 1

    def test_a_song_may_stand_without_a_loop(self) -> None:
        song = player_song(resting_streams((SOUNDING,)), NTSC_FREQUENCY, loop_tick=None)
        assert song.loop_tick is None

    def test_a_loop_at_the_songs_length_raises(self) -> None:
        with pytest.raises(ValidationError, match="loop_tick must lie within"):
            player_song(resting_streams((SOUNDING, OCTAVE_UP)), NTSC_FREQUENCY, loop_tick=2)

    def test_a_negative_loop_raises(self) -> None:
        with pytest.raises(ValidationError, match="loop_tick must lie within"):
            player_song(resting_streams((SOUNDING,)), NTSC_FREQUENCY, loop_tick=-1)

    def test_the_song_stays_as_built(self) -> None:
        song = player_song(resting_streams((SOUNDING,)), NTSC_FREQUENCY, loop_tick=None)
        with pytest.raises(ValidationError):
            song.loop_tick = 0


class TestSongPlayback(BaseTestSuite):
    """The tick each call lands on, read across a song that ends and one that repeats."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Tuple[Optional[int], ...]
        name: str
        loop_tick: Optional[int]

        @property
        def label(self) -> str:
            return self.name

        @property
        def song(self) -> Song:
            return player_song(
                resting_streams((SOUNDING, OCTAVE_UP, RESTING, RESTING)),
                NTSC_FREQUENCY,
                self.loop_tick,
            )

    test_cases: Tuple[TestCase, ...] = (
        TestCase(name="stops", loop_tick=None, expected=(0, 1, 2, 3, None, None, None, None)),
        TestCase(name="repeats-from-the-start", loop_tick=0, expected=(0, 1, 2, 3, 0, 1, 2, 3)),
        TestCase(name="repeats-from-the-middle", loop_tick=2, expected=(0, 1, 2, 3, 2, 3, 2, 3)),
        TestCase(name="repeats-one-tick", loop_tick=3, expected=(0, 1, 2, 3, 3, 3, 3, 3)),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_calls_land_where_expected(self, test_case: TestCase) -> None:
        song = test_case.song
        ticks = tuple(song.tick_at(play_call) for play_call in range(len(test_case.expected)))
        assert ticks == test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_every_tick_played_lies_within_the_song(self, test_case: TestCase) -> None:
        song = test_case.song
        played = [song.tick_at(play_call) for play_call in range(len(test_case.expected))]
        assert all(0 <= tick < song.ticks for tick in played if tick is not None)

    def test_the_song_lasts_as_long_as_its_streams(self) -> None:
        song = player_song(resting_streams((SOUNDING, OCTAVE_UP)), NTSC_FREQUENCY, loop_tick=None)
        assert song.ticks == song.streams.ticks

    def test_a_slow_stream_holds_its_tick_between_calls(self) -> None:
        song = player_song(resting_streams((SOUNDING, OCTAVE_UP, RESTING, RESTING)), 30, loop_tick=None)
        assert tuple(song.tick_at(play_call) for play_call in range(6)) == (0, 0, 1, 1, 2, 2)
