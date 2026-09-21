from typing import Final

import pytest

from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.specification.planes import (
    PLANE_COUNT,
    PLANE_NAMES,
    PLANES,
    PlaneRole,
    channel_indices,
    plane_index,
)

PLANES_A_CHANNEL_SOUNDS_WITH: Final[int] = 2


class TestOneTableStatesEveryPlaneASongBlockWrites:
    """The song block writes its planes in one order, and the table is where that order is stated."""

    def test_every_channel_writes_what_it_sounds_and_how_it_sounds_it(self) -> None:
        for channel in ChannelName.items():
            roles = {PLANES[index].role for index in channel_indices(channel)}

            assert {PlaneRole.CONTROL, PlaneRole.VALUE} <= roles

    def test_a_bend_belongs_to_each_channel_whose_divider_moves(self) -> None:
        bending = {PLANES[index].channel for index, plane in enumerate(PLANES) if plane.spans_flagged_ticks}

        assert bending == TONE_CHANNELS

    def test_a_plane_is_named_by_the_channel_and_the_part_it_carries(self) -> None:
        assert PLANES[plane_index(ChannelName.NOISE, PlaneRole.VALUE)].name == "noise_value"

    def test_the_table_names_each_plane_once(self) -> None:
        assert len(set(PLANE_NAMES)) == PLANE_COUNT

    def test_a_channel_writing_no_plane_for_a_role_is_refused(self) -> None:
        with pytest.raises(ValueError, match="writes no bend plane"):
            plane_index(ChannelName.NOISE, PlaneRole.BEND)


class TestTheStreamsStandUnderTheNamesTheTableStates:
    """A stream is reached by its own name, and the names are the table's — a test keeps them one."""

    def test_the_streams_carry_the_names_the_table_states(self) -> None:
        assert PlaneOrder._fields == PLANE_NAMES

    def test_the_noise_channel_reads_no_bend(self) -> None:
        assert len(channel_indices(ChannelName.NOISE)) == PLANES_A_CHANNEL_SOUNDS_WITH
