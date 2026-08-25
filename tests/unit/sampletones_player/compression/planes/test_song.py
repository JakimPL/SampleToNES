from typing import Final

import pytest
from pydantic import ValidationError

from sampletones_player.compression.planes.channel import ChannelPlanes, TonePlanes
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.specification.compression import PLANE_COUNT

BEND: Final[bytes] = bytes((0x00, 0xFD))


def song(control: bytes, value: bytes) -> SongPlanes:
    channel = TonePlanes(control=control, value=value, bend=BEND)
    resting = TonePlanes(
        control=bytes(len(control)),
        value=bytes(len(value)),
        bend=bytes(len(control)),
    )
    silent = ChannelPlanes(control=bytes(len(control)), value=bytes(len(value)))
    return SongPlanes(pulse1=channel, pulse2=resting, triangle=resting, noise=silent)


class TestASongGathersItsChannelsPlanes:
    """Every plane advances beside the rest, so the song states them all under one length."""

    def test_a_song_carries_the_planes_a_block_writes(self) -> None:
        assert len(song(bytes((1, 2)), bytes((3, 4))).planes) == PLANE_COUNT

    def test_the_planes_read_back_under_the_channels_that_write_them(self) -> None:
        planes = song(bytes((1, 2)), bytes((3, 4)))
        assert SongPlanes.from_order(planes.planes) == planes

    def test_a_tone_channels_bend_reaches_the_block_beside_its_pitch(self) -> None:
        planes = song(bytes((1, 2)), bytes((3, 4))).planes
        assert planes.pulse1_bend == BEND

    def test_a_song_lasts_the_ticks_its_channels_cover(self) -> None:
        assert song(bytes((1, 2)), bytes((3, 4))).ticks == 2

    def test_channels_covering_different_ticks_are_refused(self) -> None:
        short = TonePlanes(control=bytes(1), value=bytes(1), bend=bytes(1))
        long = TonePlanes(control=bytes(2), value=bytes(2), bend=bytes(2))
        with pytest.raises(ValidationError):
            SongPlanes(
                pulse1=short,
                pulse2=long,
                triangle=short,
                noise=ChannelPlanes(control=bytes(1), value=bytes(1)),
            )
