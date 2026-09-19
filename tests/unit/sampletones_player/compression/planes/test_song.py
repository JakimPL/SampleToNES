from typing import Final, Tuple

import pytest
from pydantic import ValidationError

from sampletones_player.compression.planes.channel import ChannelPlanes, TonePlanes
from sampletones_player.compression.planes.flags import flagged_value
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.specification.compression import PLANE_COUNT

BEND: Final[bytes] = bytes((0x00, 0xFD))
FLAGGED: Final[bytes] = bytes((flagged_value(3, True), flagged_value(4, True)))
PULSE1_BEND: Final[int] = 2
BENDS: Final[Tuple[str, ...]] = ("pulse1_bend", "pulse2_bend", "triangle_bend")


def song(control: bytes, value: bytes, bend: bytes) -> SongPlanes:
    channel = TonePlanes(control=control, value=value, bend=bend)
    resting = TonePlanes(control=bytes(len(control)), value=bytes(len(value)), bend=b"")
    silent = ChannelPlanes(control=bytes(len(control)), value=bytes(len(value)))
    return SongPlanes(pulse1=channel, pulse2=resting, triangle=resting, noise=silent)


class TestASongGathersItsChannelsPlanes:
    """Every plane advances beside the rest, so the song states them all under one length."""

    def test_a_song_carries_the_planes_a_block_writes(self) -> None:
        assert len(song(bytes((1, 2)), FLAGGED, BEND).planes) == PLANE_COUNT

    def test_the_planes_read_back_under_the_channels_that_write_them(self) -> None:
        planes = song(bytes((1, 2)), FLAGGED, BEND)
        assert SongPlanes.from_order(planes.planes) == planes

    def test_a_tone_channels_bend_reaches_the_block_beside_its_pitch(self) -> None:
        planes = song(bytes((1, 2)), FLAGGED, BEND).planes
        assert planes.pulse1_bend == BEND

    def test_a_song_lasts_the_ticks_its_channels_cover(self) -> None:
        assert song(bytes((1, 2)), FLAGGED, BEND).ticks == 2

    def test_channels_covering_different_ticks_are_refused(self) -> None:
        short = TonePlanes(control=bytes(1), value=bytes(1), bend=b"")
        long = TonePlanes(control=bytes(2), value=bytes(2), bend=b"")
        with pytest.raises(ValidationError):
            SongPlanes(
                pulse1=short,
                pulse2=long,
                triangle=short,
                noise=ChannelPlanes(control=bytes(1), value=bytes(1)),
            )


class TestABendPlaneCoversTheFlaggedTicks:
    """A bend plane holds a value for each tick its value plane flags, and for those alone."""

    def test_a_bend_for_every_flagged_tick_is_taken(self) -> None:
        value = bytes((flagged_value(3, False), flagged_value(3, True)))
        assert TonePlanes(control=bytes(2), value=value, bend=BEND[:1]).bend == BEND[:1]

    def test_a_bend_plane_holding_more_than_the_flags_ask_for_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            TonePlanes(control=bytes(2), value=bytes((3, 4)), bend=BEND)

    def test_a_bend_plane_holding_fewer_than_the_flags_ask_for_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            TonePlanes(control=bytes(2), value=FLAGGED, bend=BEND[:1])

    def test_a_song_returning_to_a_tick_re_enters_the_bend_plane_past_the_flags_before_it(self) -> None:
        value = bytes((flagged_value(3, True), flagged_value(3, False), flagged_value(3, True)))
        planes = song(bytes(3), value, BEND)
        assert [planes.positions(tick)[PULSE1_BEND] for tick in range(4)] == [0, 1, 1, 2]
        dense = [position for name, position in zip(PlaneOrder.names(), planes.positions(2)) if name not in BENDS]
        assert dense == [2] * len(dense)
