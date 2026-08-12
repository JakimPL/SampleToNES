from typing import Optional

import pytest
from pydantic import ValidationError

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.view_model.sequencer.region import (
    OrderRegion,
    TrackerRegion,
)
from sampletones_application.view_model.sequencer.slot import (
    SLOT_COUNT,
    TrackerSlot,
    slot_from_flat,
)
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName


class TestTrackerRegion:
    def test_a_single_cell_region_covers_that_cell(self) -> None:
        region = TrackerRegion(first_row=3, last_row=3, first_slot=4, last_slot=4)

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

        assert tuple(region.rows) == tuple(range(64))
        assert region.slots == tuple(slot_from_flat(index) for index in range(SLOT_COUNT))

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
        assert tuple(region.positions) == tuple(range(8))

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


class TestTrackerRegionMembership:
    """Which cells a rectangle holds, which is what a gesture raised on one asks."""

    @pytest.fixture
    def region(self) -> TrackerRegion:
        return TrackerRegion(first_row=2, last_row=5, first_slot=3, last_slot=7)

    @pytest.mark.parametrize(
        ("row", "slot_index"),
        [
            (2, 3),
            (5, 7),
            (3, 5),
        ],
    )
    def test_a_cell_inside_the_rectangle_belongs_to_it(
        self,
        region: TrackerRegion,
        row: int,
        slot_index: int,
    ) -> None:
        assert region.covers(row, slot_from_flat(slot_index)) is True

    @pytest.mark.parametrize(
        ("row", "slot_index"),
        [
            (1, 5),
            (6, 5),
            (3, 2),
            (3, 8),
        ],
    )
    def test_a_cell_outside_the_rectangle_stands_on_its_own(
        self,
        region: TrackerRegion,
        row: int,
        slot_index: int,
    ) -> None:
        assert region.covers(row, slot_from_flat(slot_index)) is False


class TestOrderRegionMembership:
    @pytest.fixture
    def region(self) -> OrderRegion:
        return OrderRegion(first_row=1, last_row=2, first_position=3, last_position=6)

    @pytest.mark.parametrize(
        ("generator", "position"),
        [
            (GeneratorName.PULSE1, 3),
            (GeneratorName.PULSE2, 6),
            (GeneratorName.PULSE1, 5),
        ],
    )
    def test_a_cell_inside_the_rectangle_belongs_to_it(
        self,
        region: OrderRegion,
        generator: GeneratorName,
        position: int,
    ) -> None:
        assert region.covers(generator, position) is True

    @pytest.mark.parametrize(
        ("generator", "position"),
        [
            (None, 5),
            (GeneratorName.TRIANGLE, 5),
            (GeneratorName.PULSE1, 2),
            (GeneratorName.PULSE1, 7),
        ],
    )
    def test_a_cell_outside_the_rectangle_stands_on_its_own(
        self,
        region: OrderRegion,
        generator: Optional[GeneratorName],
        position: int,
    ) -> None:
        assert region.covers(generator, position) is False
