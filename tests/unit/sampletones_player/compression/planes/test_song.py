import pytest
from pydantic import ValidationError

from sampletones_player.compression.planes.channel import ChannelPlanes
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.specification.compression import PLANE_COUNT


def song(control: bytes, value: bytes) -> SongPlanes:
    channel = ChannelPlanes(control=control, value=value)
    resting = ChannelPlanes(control=bytes(len(control)), value=bytes(len(value)))
    return SongPlanes(pulse1=channel, pulse2=resting, triangle=resting, noise=resting)


class TestASongGathersItsChannelsPlanes:
    """The eight planes advance together, so the song states them under one length."""

    def test_a_song_carries_two_planes_for_every_channel(self) -> None:
        assert len(song(bytes((1, 2)), bytes((3, 4))).planes) == PLANE_COUNT

    def test_the_planes_read_back_under_the_channels_that_write_them(self) -> None:
        planes = song(bytes((1, 2)), bytes((3, 4)))
        assert SongPlanes.from_order(planes.planes) == planes

    def test_a_song_lasts_the_ticks_its_channels_cover(self) -> None:
        assert song(bytes((1, 2)), bytes((3, 4))).ticks == 2

    def test_channels_covering_different_ticks_are_refused(self) -> None:
        short = ChannelPlanes(control=bytes(1), value=bytes(1))
        long = ChannelPlanes(control=bytes(2), value=bytes(2))
        with pytest.raises(ValidationError):
            SongPlanes(pulse1=short, pulse2=long, triangle=short, noise=short)
