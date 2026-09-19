from typing import Final

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.flags import flagged_value
from sampletones_player.compression.planes.separate import channel_planes, planes_from_streams
from sampletones_player.registers.pulse import PulseRegisters
from sampletones_player.registers.streams import ChannelStreams
from sampletones_player.specification.binary import SIGNED_BYTE_LIMIT, unsigned_byte
from sampletones_player.specification.registers import MAX_REGISTER_VALUE, TIMER_HIGH_SHIFT
from tests.suite.player import PLAYER_FULL_VOLUME, resting_streams
from tests.unit.sampletones_player.compression.planes.conftest import (
    HIGH_INDEX,
    LOW_INDEX,
    NOISE_PERIOD,
    SOUNDING_TICKS,
)

PAST_HALFWAY: Final[int] = -40


def anchored_tick(pitches: PitchTable, index: int, bend: int) -> PulseRegisters:
    """A sounding pulse tick counted from the pitch at ``index``, bent by ``bend`` steps."""
    divider = pitches.timers[index] + bend
    return PulseRegisters(
        control=PLAYER_FULL_VOLUME,
        timer_low=divider & MAX_REGISTER_VALUE,
        timer_high=divider >> TIMER_HIGH_SHIFT,
        anchor=pitches.pitch(index),
    )


class TestAChannelSeparatesIntoTwoPlanes:
    """A channel writes how it sounds and what it sounds, and each turns over at its own pace."""

    def test_a_tone_channel_names_its_pitch_rather_than_its_divider(
        self,
        sounding_streams: ChannelStreams,
        pitches: PitchTable,
    ) -> None:
        planes = planes_from_streams(sounding_streams, pitches)
        assert planes.pulse1.value == bytes((LOW_INDEX, HIGH_INDEX, HIGH_INDEX))

    def test_the_noise_channel_names_the_period_its_register_takes(
        self,
        sounding_streams: ChannelStreams,
        pitches: PitchTable,
    ) -> None:
        planes = planes_from_streams(sounding_streams, pitches)
        assert planes.noise.value == bytes((NOISE_PERIOD,)) * planes.ticks

    def test_a_channel_running_out_early_holds_its_values_through_the_song(
        self,
        sounding_streams: ChannelStreams,
        pitches: PitchTable,
    ) -> None:
        planes = planes_from_streams(sounding_streams, pitches)
        assert planes.ticks == SOUNDING_TICKS
        assert planes.pulse2.control == bytes((planes.pulse2.control[0],)) * SOUNDING_TICKS

    def test_one_channel_separates_the_same_way_the_song_does(
        self,
        sounding_streams: ChannelStreams,
        pitches: PitchTable,
    ) -> None:
        planes = planes_from_streams(sounding_streams, pitches)
        pulse1 = channel_planes(ChannelName.PULSE1, sounding_streams.padded[0], pitches)
        assert pulse1 == planes.pulse1


class TestABentTickSplitsIntoANoteAndABend:
    """A tick's divider reaches the planes as the pitch it is counted from and the steps from there."""

    def test_an_unbent_tick_holds_a_bend_of_nothing(
        self,
        sounding_streams: ChannelStreams,
        pitches: PitchTable,
    ) -> None:
        planes = planes_from_streams(sounding_streams, pitches)
        assert planes.pulse1.bend == b""

    def test_a_bent_tick_names_its_anchor_and_the_steps_from_it(self, pitches: PitchTable) -> None:
        bends = (2, -3, PAST_HALFWAY)
        streams = resting_streams([anchored_tick(pitches, LOW_INDEX, bend) for bend in bends])
        planes = planes_from_streams(streams, pitches)
        assert planes.pulse1.value == bytes(flagged_value(LOW_INDEX, True) for _ in bends)
        assert planes.pulse1.bend == bytes(unsigned_byte(bend) for bend in bends)

    def test_a_note_is_flagged_from_its_first_bend_to_its_last(self, pitches: PitchTable) -> None:
        bends = (0, 3, 0, -3, 0)
        streams = resting_streams([anchored_tick(pitches, LOW_INDEX, bend) for bend in bends])
        planes = planes_from_streams(streams, pitches)
        assert planes.pulse1.value == bytes(flagged_value(LOW_INDEX, 0 < tick < 4) for tick in range(len(bends)))
        assert planes.pulse1.bend == bytes(unsigned_byte(bend) for bend in bends[1:4])

    def test_a_divider_past_the_byte_from_its_anchor_is_refused(self, pitches: PitchTable) -> None:
        streams = resting_streams((anchored_tick(pitches, LOW_INDEX, -SIGNED_BYTE_LIMIT - 1),))
        with pytest.raises(ValueError):
            planes_from_streams(streams, pitches)
