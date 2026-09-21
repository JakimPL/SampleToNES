from typing import Final, Tuple

import pytest
from pydantic import ValidationError

from sampletones_core.constants.enums import ChannelName
from sampletones_player.compression.planes.flags import flagged_value
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.specification.planes import (
    PLANE_COUNT,
    PLANES,
    PlaneRole,
    plane_index,
)
from tests.suite.player import sounding_planes

BEND: Final[bytes] = bytes((0x00, 0xFD))
FLAGGED: Final[bytes] = bytes((flagged_value(3, True), flagged_value(4, True)))
PULSE1_BEND: Final[int] = plane_index(ChannelName.PULSE1, PlaneRole.BEND)
BENDS: Final[Tuple[str, ...]] = tuple(plane.name for plane in PLANES if plane.spans_flagged_ticks)


class TestASongGathersEveryPlaneItsBlockWrites:
    """Every plane advances beside the rest, so the song states them all under one length."""

    def test_a_song_carries_the_planes_a_block_writes(self) -> None:
        assert len(sounding_planes(bytes((1, 2)), FLAGGED, BEND).planes) == PLANE_COUNT

    def test_a_plane_is_reached_by_the_name_the_block_writes_it_under(self) -> None:
        planes = sounding_planes(bytes((1, 2)), FLAGGED, BEND).planes

        assert planes.pulse1_bend == BEND

    def test_a_channel_answers_with_the_planes_it_writes(self) -> None:
        planes = sounding_planes(bytes((1, 2)), FLAGGED, BEND)

        assert planes.of(ChannelName.PULSE1) == (bytes((1, 2)), FLAGGED, BEND)

    def test_a_song_lasts_the_ticks_its_planes_cover(self) -> None:
        assert sounding_planes(bytes((1, 2)), FLAGGED, BEND).ticks == 2

    def test_planes_covering_different_ticks_are_refused(self) -> None:
        with pytest.raises(ValidationError):
            SongPlanes(planes=PlaneOrder.across(bytes(plane) for plane in range(1, PLANE_COUNT + 1)))

    def test_planes_covering_no_tick_are_refused(self) -> None:
        with pytest.raises(ValidationError):
            SongPlanes(planes=PlaneOrder.across(b"" for _ in range(PLANE_COUNT)))


class TestABendPlaneCoversTheFlaggedTicks:
    """A bend plane holds a value for each tick its value plane flags, and for those alone."""

    def test_a_bend_for_every_flagged_tick_is_taken(self) -> None:
        value = bytes((flagged_value(3, False), flagged_value(3, True)))

        assert sounding_planes(bytes(2), value, BEND[:1]).planes.pulse1_bend == BEND[:1]

    def test_a_bend_plane_holding_more_than_the_flags_ask_for_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            sounding_planes(bytes(2), bytes((3, 4)), BEND)

    def test_a_bend_plane_holding_fewer_than_the_flags_ask_for_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            sounding_planes(bytes(2), FLAGGED, BEND[:1])

    def test_a_song_returning_to_a_tick_re_enters_the_bend_plane_past_the_flags_before_it(self) -> None:
        value = bytes((flagged_value(3, True), flagged_value(3, False), flagged_value(3, True)))
        planes = sounding_planes(bytes(3), value, BEND)

        assert [planes.positions(tick)[PULSE1_BEND] for tick in range(4)] == [0, 1, 1, 2]
        dense = [position for name, position in zip(PlaneOrder.names(), planes.positions(2)) if name not in BENDS]
        assert dense == [2] * len(dense)
