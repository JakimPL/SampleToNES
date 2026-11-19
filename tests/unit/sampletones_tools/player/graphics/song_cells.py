import math
from dataclasses import dataclass
from typing import Final, List, Sequence, Tuple

from sampletones_player.compression.pitch import PITCH_COUNT
from sampletones_player.specification.screen import TILE_SIDE
from sampletones_tools.player.graphics.deck.markers import PIXELS_PER_PITCH
from sampletones_tools.player.graphics.deck.meters import meter_members
from sampletones_tools.player.graphics.deck.state import MAX_LEVEL
from sampletones_tools.player.graphics.deck.texts import REST_NOTE, clock_text
from sampletones_tools.player.graphics.deck.waves import PULSE_REST, WAVE_PERIODS
from sampletones_tools.player.graphics.layout.fields import TextField
from sampletones_tools.player.graphics.layout.screen import ScreenLayout

CellPosition = Tuple[int, int]

FIRST_SAFE_COLUMN: Final[int] = 2
LAST_SAFE_COLUMN: Final[int] = 29
FIRST_SAFE_ROW: Final[int] = 3
LAST_SAFE_ROW: Final[int] = 26
FIRST_ACTION_COLUMN: Final[int] = 1
LAST_ACTION_COLUMN: Final[int] = 30
FIRST_ACTION_ROW: Final[int] = 1
LAST_ACTION_ROW: Final[int] = 28

ONE_ROW: Final[int] = 1
ONE_CELL: Final[int] = 1
WAVE_ROWS: Final[int] = 2
WAVE_CELLS: Final[int] = WAVE_PERIODS * len(PULSE_REST.top)
NOTE_CELLS: Final[int] = len(REST_NOTE)
METER_CELLS: Final[int] = len(meter_members(MAX_LEVEL))
CLOCK_CELLS: Final[int] = len(clock_text(0))
KEYBOARD_CELLS: Final[int] = math.ceil(PITCH_COUNT * PIXELS_PER_PITCH / TILE_SIDE)


def title_safe(row: int, column: int) -> bool:
    """Whether a cell lies in the television title-safe area of a 256x240 picture.

    The area spans columns 2-29 and rows 3-26, the part of the picture every set shows.
    """
    return FIRST_SAFE_ROW <= row <= LAST_SAFE_ROW and FIRST_SAFE_COLUMN <= column <= LAST_SAFE_COLUMN


def action_safe(row: int, column: int) -> bool:
    """Whether a cell lies in the television action-safe area of a 256x240 picture.

    The area spans columns 1-30 and rows 1-28, the part of the picture nearly every set shows.
    """
    return FIRST_ACTION_ROW <= row <= LAST_ACTION_ROW and FIRST_ACTION_COLUMN <= column <= LAST_ACTION_COLUMN


@dataclass(frozen=True)
class Span:
    """A block of cells a song is written to."""

    row: int
    column: int
    width: int
    height: int

    @property
    def cells(self) -> List[CellPosition]:
        return [(self.row + row, self.column + column) for row in range(self.height) for column in range(self.width)]


def program_line(field: TextField) -> List[Span]:
    return [Span(row=field.row, column=field.column, width=field.width, height=ONE_ROW)]


def transport_cells(layout: ScreenLayout, column: int, width: int) -> List[Span]:
    return [Span(row=layout.transport.row, column=column, width=width, height=ONE_ROW)]


def progress_bar(layout: ScreenLayout) -> List[Span]:
    progress = layout.progress
    return [Span(row=progress.row, column=progress.column, width=progress.width, height=ONE_ROW)]


def channel(layout: ScreenLayout, row: int) -> List[Span]:
    """What a channel writes: its wave over two rows, and its note and meter in the upper one."""
    channels = layout.channels
    return [
        Span(row=row, column=channels.wave_column, width=WAVE_CELLS, height=WAVE_ROWS),
        Span(row=row, column=channels.note_column, width=NOTE_CELLS, height=ONE_ROW),
        Span(row=row, column=channels.meter_column, width=METER_CELLS, height=ONE_ROW),
    ]


def keyboard_row(layout: ScreenLayout, row: int) -> List[Span]:
    return [Span(row=row, column=layout.keyboard.column, width=KEYBOARD_CELLS, height=ONE_ROW)]


def cells_of(spans: Sequence[Span]) -> List[CellPosition]:
    return [cell for span in spans for cell in span.cells]
