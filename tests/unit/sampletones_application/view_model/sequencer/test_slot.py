from typing import Optional

import pytest

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.view_model.sequencer.slot import (
    SLOT_COUNT,
    SUBCOLUMNS,
    TrackerSlot,
    column_slot_base,
    slot_from_flat,
)
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName

_OUT_OF_RANGE = [-1, -SLOT_COUNT, SLOT_COUNT, SLOT_COUNT + 1]


class TestAxis:
    def test_the_sample_column_leads_the_four_channels(self) -> None:
        assert CHANNEL_AXIS == (None, *ChannelName.items())

    def test_the_axis_covers_every_column_once_over(self) -> None:
        assert SLOT_COUNT == len(CHANNEL_AXIS) * len(SUBCOLUMNS)


class TestFlatIndex:
    @pytest.mark.parametrize("index", range(SLOT_COUNT))
    def test_every_index_round_trips_through_its_slot(self, index: int) -> None:
        assert slot_from_flat(index).flat_index == index

    def test_the_axis_maps_onto_the_whole_index_range(self) -> None:
        indices = {TrackerSlot(channel, subcolumn).flat_index for channel in CHANNEL_AXIS for subcolumn in SUBCOLUMNS}

        assert indices == set(range(SLOT_COUNT))

    def test_the_sample_columns_instrument_opens_the_axis(self) -> None:
        assert TrackerSlot(None, SubColumn.INSTRUMENT).flat_index == 0


class TestColumnBase:
    @pytest.mark.parametrize("channel", CHANNEL_AXIS)
    def test_every_base_starts_a_whole_column(self, channel: Optional[ChannelName]) -> None:
        """Kind alignment rests on this: an offset from any base addresses the same subcolumn."""
        assert column_slot_base(channel) % len(SUBCOLUMNS) == 0

    @pytest.mark.parametrize("channel", CHANNEL_AXIS)
    def test_a_base_addresses_its_columns_first_subcolumn(self, channel: Optional[ChannelName]) -> None:
        assert slot_from_flat(column_slot_base(channel)) == TrackerSlot(channel, SUBCOLUMNS[0])


class TestBounds:
    @pytest.mark.parametrize("index", _OUT_OF_RANGE)
    def test_an_index_off_the_axis_is_rejected(self, index: int) -> None:
        """A selection clips at the edge, so a slot outside the axis is a caller's mistake."""
        with pytest.raises(IndexError):
            slot_from_flat(index)
