from sampletones_core.constants.general import MAX_TIMER, MIN_TIMER
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.rebuild import streams_from_planes
from sampletones_player.compression.planes.separate import planes_from_streams
from sampletones_player.registers.streams import ChannelStreams
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    noise_tick,
    player_streams,
    pulse_tick,
    triangle_tick,
)
from tests.unit.sampletones_player.compression.planes.conftest import (
    NOISE_PERIOD,
)


class TestThePlanesReadBackAsTheStreamsTheyCameFrom:
    """The separation is a reading of the streams, so it carries every register value."""

    def test_a_song_rebuilds_from_its_planes(
        self,
        sounding_streams: ChannelStreams,
        pitches: PitchTable,
    ) -> None:
        planes = planes_from_streams(sounding_streams, pitches)
        rebuilt = streams_from_planes(planes, pitches)
        for tick in range(sounding_streams.ticks):
            assert rebuilt.at(tick) == sounding_streams.at(tick)

    def test_every_divider_the_register_holds_rebuilds(self, pitches: PitchTable) -> None:
        """A bent tick may sound any divider, and the index and bend it splits into sum back to it."""
        dividers = range(MIN_TIMER, MAX_TIMER + 1)
        streams = player_streams(
            pulse1=[pulse_tick(PLAYER_FULL_VOLUME, 0, divider) for divider in dividers],
            pulse2=[pulse_tick(PLAYER_FULL_VOLUME, 1, divider) for divider in reversed(dividers)],
            triangle=[triangle_tick(True, divider) for divider in dividers],
            noise=[noise_tick(PLAYER_FULL_VOLUME, 0, NOISE_PERIOD)],
        )
        rebuilt = streams_from_planes(planes_from_streams(streams, pitches), pitches)
        assert [rebuilt.at(tick) for tick in range(streams.ticks)] == [
            streams.at(tick) for tick in range(streams.ticks)
        ]
