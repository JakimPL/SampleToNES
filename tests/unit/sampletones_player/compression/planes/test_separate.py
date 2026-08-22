from sampletones_core.constants.enums import ChannelName
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.separate import channel_planes, planes_from_streams
from sampletones_player.registers.streams import ChannelStreams
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
