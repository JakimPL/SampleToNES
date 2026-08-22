from typing import Final, Optional, Tuple

import pytest

from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.song import compress_song, decompress_song
from sampletones_player.registers.streams import ChannelStreams
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    PLAYER_OCTAVE_UP_TIMER,
    PLAYER_PITCHES,
    PLAYER_REFERENCE_TIMER,
    PLAYER_SILENT_VOLUME,
    pulse_tick,
    resting_streams,
)

SOUNDING: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_REFERENCE_TIMER)
RESTING: Final = pulse_tick(PLAYER_SILENT_VOLUME, 0, PLAYER_REFERENCE_TIMER)
OCTAVE_UP: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_OCTAVE_UP_TIMER)

HELD_TICKS: Final[int] = 12
MIDDLE_TICK: Final[int] = 6
UNSOUNDED_TIMER: Final[int] = 0x154
NO_SEEDS: Final[Tuple[Phrase, ...]] = ()


def played(
    streams: ChannelStreams,
    loop_tick: Optional[int] = None,
) -> ChannelStreams:
    return decompress_song(
        compress_song(
            streams,
            PLAYER_PITCHES,
            seeds=NO_SEEDS,
            loop_tick=loop_tick,
        ),
        PLAYER_PITCHES,
    )


class TestTheSongPlaysBackTheRegistersItWasCompressedFrom:
    """What the codec is held to at the song level: every channel writes what it was given."""

    def test_every_tick_writes_the_registers_it_was_given(self) -> None:
        streams = resting_streams((SOUNDING, OCTAVE_UP, RESTING))
        rebuilt = played(streams)
        assert [rebuilt.at(tick) for tick in range(streams.ticks)] == [
            streams.at(tick) for tick in range(streams.ticks)
        ]

    def test_a_channel_running_out_early_is_carried_to_the_songs_length(self) -> None:
        streams = resting_streams((SOUNDING, OCTAVE_UP, RESTING))
        rebuilt = played(streams)
        assert len(rebuilt.noise) == streams.ticks
        assert set(rebuilt.noise) == {streams.noise[0]}


class TestASongThatRepeatsReEntersItsStreams:
    """A loop returns partway through, so the tick it returns to starts a token of its own."""

    def test_the_tick_a_song_returns_to_costs_the_streams_a_token(self) -> None:
        """Splitting a run at the loop tick is what leaves the driver a token to resume on."""
        streams = resting_streams((SOUNDING,) * HELD_TICKS)
        looped = compress_song(
            streams,
            PLAYER_PITCHES,
            seeds=NO_SEEDS,
            loop_tick=MIDDLE_TICK,
        )
        played_once = compress_song(
            streams,
            PLAYER_PITCHES,
            seeds=NO_SEEDS,
            loop_tick=None,
        )
        assert looped.size > played_once.size

    def test_the_song_writes_the_same_registers_either_way(self) -> None:
        streams = resting_streams((SOUNDING,) * HELD_TICKS)
        assert played(streams, MIDDLE_TICK) == played(streams)


class TestAPlaneNamesPitchesTheTableSounds:
    """A tone channel reaches a plane as pitch indices, so its timers are the table's own."""

    def test_a_timer_no_pitch_sounds_is_refused(self) -> None:
        streams = resting_streams((pulse_tick(PLAYER_FULL_VOLUME, 0, UNSOUNDED_TIMER),))
        with pytest.raises(ValueError, match=str(UNSOUNDED_TIMER)):
            compress_song(
                streams,
                PLAYER_PITCHES,
                seeds=NO_SEEDS,
                loop_tick=None,
            )
