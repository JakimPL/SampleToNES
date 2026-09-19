from sampletones_core.constants.enums import ChannelName
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.separate import channel_planes, planes_from_streams
from sampletones_player.registers.streams import ChannelStreams
from sampletones_player.specification.binary import unsigned_byte
from tests.suite.player import PLAYER_FULL_VOLUME, pulse_tick, resting_streams
from tests.unit.sampletones_player.compression.planes.conftest import (
    HIGH_INDEX,
    LOW_INDEX,
    NOISE_PERIOD,
    SOUNDING_TICKS,
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
    """A divider the table holds nowhere reaches the planes as the index nearest it and the rest."""

    def test_an_unbent_tick_holds_a_bend_of_nothing(
        self,
        sounding_streams: ChannelStreams,
        pitches: PitchTable,
    ) -> None:
        planes = planes_from_streams(sounding_streams, pitches)
        assert planes.pulse1.bend == bytes(planes.ticks)

    def test_a_bent_tick_names_the_index_nearest_it_and_the_steps_left_over(self, pitches: PitchTable) -> None:
        bends = (2, -3)
        streams = resting_streams(
            [pulse_tick(PLAYER_FULL_VOLUME, 0, pitches.timers[LOW_INDEX] + bend) for bend in bends]
        )
        planes = planes_from_streams(streams, pitches)
        assert planes.pulse1.value == bytes((LOW_INDEX,) * len(bends))
        assert planes.pulse1.bend == bytes(unsigned_byte(bend) for bend in bends)

    def test_a_divider_past_halfway_names_the_neighboring_index(self, pitches: PitchTable) -> None:
        lower, higher = pitches.timers[LOW_INDEX], pitches.timers[LOW_INDEX + 1]
        divider = higher + 1
        streams = resting_streams((pulse_tick(PLAYER_FULL_VOLUME, 0, divider),))
        planes = planes_from_streams(streams, pitches)
        assert lower - divider > divider - higher
        assert (planes.pulse1.value[0], planes.pulse1.bend[0]) == (LOW_INDEX + 1, unsigned_byte(1))
