from typing import Optional, Self, Tuple

from pydantic import BaseModel, Field, model_validator

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.view_model.sequencer.slot import (
    SLOT_COUNT,
    TrackerSlot,
    slot_from_flat,
)
from sampletones_core.constants.enums import GeneratorName


class TrackerCell(BaseModel, frozen=True):
    """The tracker cell a block is written from: a row, and the column it starts in.

    A block carries the subcolumn offsets it was read at, so the cell it is anchored to names a
    row and a column while the block supplies the rest. That is why a cell states no subcolumn:
    the anchor decides where a block lands, and the block decides which kind of value goes where.
    """

    row: int = Field(ge=0)
    generator: Optional[GeneratorName]


class OrderCell(BaseModel, frozen=True):
    """The order cell a block is written from: a channel row, and the position it starts in."""

    generator: Optional[GeneratorName]
    position: int = Field(ge=0)


class GridRegion(BaseModel, frozen=True):
    """The rows a selection covers, shared by both sequencer grids.

    Both bounds are inclusive, so a region always covers the cell it was started from and the
    smallest one covers exactly that cell. A producer orders the bounds it was given, which is
    what makes a selection dragged upwards name the same region as one dragged down to the same
    pair of cells.
    """

    first_row: int = Field(ge=0)
    last_row: int = Field(ge=0)

    @model_validator(mode="after")
    def _validate_rows(self) -> Self:
        if self.last_row < self.first_row:
            raise ValueError(f"A region's rows end at {self.last_row}, before they begin at {self.first_row}")

        return self

    @property
    def rows(self) -> range:
        return range(self.first_row, self.last_row + 1)

    def covers_row(self, row: int) -> bool:
        return self.first_row <= row <= self.last_row


class TrackerRegion(GridRegion, frozen=True):
    """A rectangle of the tracker grid: pattern rows crossed with a run of slots.

    The slots are indices into the flattened axis :data:`SLOT_COUNT` spans, so one region reaches
    across the sample column and the channels alike and names the subcolumn it begins and ends on.
    That is what lets a selection start midway through a cell: its edges are subcolumns.
    """

    first_slot: int = Field(ge=0, lt=SLOT_COUNT)
    last_slot: int = Field(ge=0, lt=SLOT_COUNT)

    @model_validator(mode="after")
    def _validate_slots(self) -> Self:
        if self.last_slot < self.first_slot:
            raise ValueError(f"A region's slots end at {self.last_slot}, before they begin at {self.first_slot}")

        return self

    @property
    def slots(self) -> Tuple[TrackerSlot, ...]:
        """The slots the region covers, each as the column and subcolumn it addresses."""
        return tuple(slot_from_flat(index) for index in range(self.first_slot, self.last_slot + 1))

    def covers(self, row: int, slot: TrackerSlot) -> bool:
        """Whether a cell of the grid falls inside the rectangle.

        This is what a gesture raised on a cell asks to learn which block it belongs to: one
        landing inside a selection acts on the whole of it, and one landing outside acts alone.
        """
        return self.covers_row(row) and self.first_slot <= slot.flat_index <= self.last_slot


class OrderRegion(GridRegion, frozen=True):
    """A rectangle of the order table: channel rows crossed with a run of positions.

    The rows are indices into :data:`CHANNEL_AXIS`, so row ``0`` is the master row and the
    channels follow it in the order the table lays them out.
    """

    first_row: int = Field(ge=0, lt=len(CHANNEL_AXIS))
    last_row: int = Field(ge=0, lt=len(CHANNEL_AXIS))
    first_position: int = Field(ge=0)
    last_position: int = Field(ge=0)

    @model_validator(mode="after")
    def _validate_positions(self) -> Self:
        if self.last_position < self.first_position:
            raise ValueError(
                f"A region's positions end at {self.last_position}, before they begin at {self.first_position}"
            )

        return self

    @property
    def positions(self) -> range:
        return range(self.first_position, self.last_position + 1)

    @property
    def generators(self) -> Tuple[Optional[GeneratorName], ...]:
        """The rows the region covers, each as the channel it addresses, master reading ``None``."""
        return tuple(CHANNEL_AXIS[row] for row in self.rows)

    def covers(
        self,
        generator: Optional[GeneratorName],
        position: int,
    ) -> bool:
        """Whether a cell of the table falls inside the rectangle.

        This is what a gesture raised on a cell asks to learn which block it belongs to: one
        landing inside a selection acts on the whole of it, and one landing outside acts alone.
        """
        return self.covers_row(CHANNEL_AXIS.index(generator)) and position in self.positions
