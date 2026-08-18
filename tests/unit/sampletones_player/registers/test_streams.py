from typing import Final

import pytest
from pydantic import ValidationError

from sampletones_player.specification.channels import CHANNEL_ORDER
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    PLAYER_OCTAVE_UP_TIMER,
    PLAYER_REFERENCE_PERIOD,
    PLAYER_REFERENCE_TIMER,
    PLAYER_SILENT_VOLUME,
    noise_tick,
    player_streams,
    pulse_tick,
    resting_streams,
    triangle_tick,
)

SOUNDING: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_REFERENCE_TIMER)
RESTING: Final = pulse_tick(PLAYER_SILENT_VOLUME, 0, PLAYER_REFERENCE_TIMER)
OCTAVE_UP: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_OCTAVE_UP_TIMER)


class TestChannelStreams:
    """The four channels reach one common length, the longest of them stating it."""

    def test_the_longest_channel_states_the_length(self) -> None:
        streams = resting_streams((SOUNDING, OCTAVE_UP, RESTING))
        assert streams.ticks == 3

    def test_a_channel_past_its_end_holds_its_final_values(self) -> None:
        streams = resting_streams((SOUNDING, RESTING))
        _, pulse2, triangle, noise = streams.at(1)
        assert (pulse2, triangle, noise) == (streams.pulse2[0], streams.triangle[0], streams.noise[0])

    def test_every_channel_reads_its_own_tick_while_it_lasts(self) -> None:
        streams = resting_streams((SOUNDING, OCTAVE_UP))
        assert streams.at(0)[0] == SOUNDING
        assert streams.at(1)[0] == OCTAVE_UP

    def test_padding_carries_every_channel_to_the_songs_length(self) -> None:
        streams = resting_streams((SOUNDING, OCTAVE_UP, RESTING))
        assert tuple(len(stream) for stream in streams.padded) == (3, 3, 3, 3)

    def test_padding_leaves_a_full_length_channel_as_it_stands(self) -> None:
        streams = resting_streams((SOUNDING, OCTAVE_UP, RESTING))
        assert streams.padded[0] == (SOUNDING, OCTAVE_UP, RESTING)

    def test_padding_repeats_the_final_values_of_a_shorter_channel(self) -> None:
        streams = resting_streams((SOUNDING, OCTAVE_UP, RESTING))
        assert streams.padded[3] == (streams.noise[0],) * 3

    def test_the_streams_stand_in_channel_order(self) -> None:
        streams = resting_streams((SOUNDING,))
        assert streams.ordered == (streams.pulse1, streams.pulse2, streams.triangle, streams.noise)

    def test_a_channel_without_a_tick_raises(self) -> None:
        with pytest.raises(ValidationError):
            player_streams(
                pulse1=(SOUNDING,),
                pulse2=(),
                triangle=(triangle_tick(False, PLAYER_REFERENCE_TIMER),),
                noise=(noise_tick(PLAYER_SILENT_VOLUME, 0, PLAYER_REFERENCE_PERIOD),),
            )

    def test_the_streams_stay_as_built(self) -> None:
        streams = resting_streams((SOUNDING,))
        with pytest.raises(ValidationError):
            streams.pulse1 = ()
