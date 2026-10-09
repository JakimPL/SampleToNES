from dataclasses import dataclass
from math import ceil
from typing import Final

from sampletones_application.ui.panels.sequencer.columns import HEADER_TABLE_ROWS

UNMEASURED_BAND: Final[float] = 0.0


@dataclass(frozen=True)
class TrackerRows:
    """Where each row of the tracker table stands: the header, the frame, and the song either side.

    The table holds the header, then ``reach`` rows the song plays before the frame, then the
    frame's own rows, then ``reach`` rows the song plays after it. A pattern row is named by its
    index in the frame wherever it is drawn, so every highlight, lookup and reading of a row goes
    through here to find the table row it stands on.
    """

    reach: int
    frame_rows: int

    @property
    def body_rows(self) -> int:
        """How many rows scroll below the header: the frame's and those standing either side of it."""
        return 2 * self.reach + self.frame_rows

    def table_row(self, frame_row: int) -> int:
        """The table row a pattern row of the frame stands on."""
        return HEADER_TABLE_ROWS + self.body_row(frame_row)

    def body_row(self, frame_row: int) -> int:
        """How many rows scroll above a pattern row of the frame, the rows before the frame among them."""
        return self.reach + frame_row

    def lead_table_row(self, slot: int) -> int:
        """The table row the ``slot``-th row standing before the frame takes, counted from the top."""
        return HEADER_TABLE_ROWS + slot

    def trail_table_row(self, slot: int) -> int:
        """The table row the ``slot``-th row standing after the frame takes, counted from the frame."""
        return HEADER_TABLE_ROWS + self.reach + self.frame_rows + slot


@dataclass(frozen=True)
class TrackerBand:
    """The part of the tracker grid standing in view below its header, and the room it centers a row in.

    The band shows the row it follows at its center, so it needs as much room above and below a
    frame as stands above its own center row. Every row is ``row_height`` tall, which keeps both the
    room and the scroll that centers a row arithmetic.

    DearPyGui reports a child window's height and no rectangle of its own, so the band is measured
    as the window's height less the part of it the header row covers: a group around the window
    states where the window begins, and the header's cells where the header ends. Measured on a
    probe grid, the reading matches the band the table's own scroll extent leaves, and an item
    resize handler on the window reports every change to it — a resized viewport, a card above it
    collapsed or grown — on the frame it happens.
    """

    height: float
    row_height: float

    @property
    def reach(self) -> int:
        """How many rows the band holds above its center row, which is the room each side of a frame takes."""
        room = max(0.0, self.height - self.row_height) / 2
        return ceil(room / self.row_height)

    def centering(self, body_row: int) -> float:
        """The scroll that stands a row at the band's center, the row named by how many rows scroll above it."""
        return max(0.0, body_row * self.row_height + (self.row_height - self.height) / 2)
