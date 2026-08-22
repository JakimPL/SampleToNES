from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.rebuild import streams_from_planes
from sampletones_player.compression.planes.separate import planes_from_streams
from sampletones_player.registers.streams import ChannelStreams


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
