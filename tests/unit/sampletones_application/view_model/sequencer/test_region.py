import pytest
from pydantic import ValidationError

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.view_model.sequencer.region import (
    OrderRegion,
    TrackerRegion,
)
from sampletones_application.view_model.sequencer.slot import SLOT_COUNT, TrackerSlot
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName


class TestTrackerRegion:
    def test_a_single_cell_region_covers_that_cell(self) -> None:
        region = TrackerRegion(first_row=3, last_row=3, first_slot=4, last_slot=4)

        assert region.row_count == 1
        assert region.slot_count == 1
        assert tuple(region.rows) == (3,)
        assert region.slots == (TrackerSlot(GeneratorName.PULSE1, SubColumn.TRANSPOSE),)

    def test_the_slots_read_as_the_columns_and_subcolumns_they_address(self) -> None:
        """A region's edges are subcolumns, so a run reaches across a column boundary mid-cell."""
        region = TrackerRegion(first_row=0, last_row=0, first_slot=2, last_slot=3)

        assert region.slots == (
            TrackerSlot(None, SubColumn.VOLUME),
            TrackerSlot(GeneratorName.PULSE1, SubColumn.INSTRUMENT),
        )

    def test_a_region_spans_the_whole_axis(self) -> None:
        region = TrackerRegion(first_row=0, last_row=63, first_slot=0, last_slot=SLOT_COUNT - 1)

        assert region.row_count == 64
        assert region.slot_count == SLOT_COUNT

    def test_inverted_rows_are_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TrackerRegion(first_row=5, last_row=2, first_slot=0, last_slot=0)

    def test_inverted_slots_are_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TrackerRegion(first_row=0, last_row=0, first_slot=5, last_slot=2)

    @pytest.mark.parametrize("slot", [-1, SLOT_COUNT])
    def test_a_slot_off_the_axis_is_rejected(self, slot: int) -> None:
        with pytest.raises(ValidationError):
            TrackerRegion(first_row=0, last_row=0, first_slot=slot, last_slot=slot)

    def test_a_negative_row_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TrackerRegion(first_row=-1, last_row=0, first_slot=0, last_slot=0)


class TestOrderRegion:
    def test_a_single_cell_region_covers_that_cell(self) -> None:
        region = OrderRegion(first_row=0, last_row=0, first_position=2, last_position=2)

        assert region.row_count == 1
        assert region.position_count == 1
        assert region.generators == (None,)
        assert tuple(region.positions) == (2,)

    def test_the_rows_read_as_the_channels_they_address(self) -> None:
        region = OrderRegion(first_row=0, last_row=2, first_position=0, last_position=0)

        assert region.generators == (None, GeneratorName.PULSE1, GeneratorName.PULSE2)

    def test_a_region_spans_the_whole_channel_axis(self) -> None:
        region = OrderRegion(
            first_row=0,
            last_row=len(CHANNEL_AXIS) - 1,
            first_position=0,
            last_position=7,
        )

        assert region.generators == CHANNEL_AXIS
        assert region.position_count == 8

    def test_inverted_positions_are_rejected(self) -> None:
        with pytest.raises(ValidationError):
            OrderRegion(first_row=0, last_row=0, first_position=5, last_position=2)

    def test_a_row_off_the_channel_axis_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            OrderRegion(
                first_row=0,
                last_row=len(CHANNEL_AXIS),
                first_position=0,
                last_position=0,
            )
