from dataclasses import dataclass
from itertools import pairwise
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from automation.boundaries.highlights import HighlightKind
from automation.dearpygui.geometry import Rect
from automation.dearpygui.items.reading import read_item
from automation.screen import Screen
from automation.views.tracker import caret_mark, frame_rows, tracker_cell
from sampletones_application.tags.sequencer import TAG_SEQUENCER_TRACKER_TABLE
from sampletones_application.ui.panels.sequencer.columns import tracker_table_column
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from tests.screens.sequencer.tracker.caret.constants import COLOR_TOLERANCE, RGB


@dataclass(frozen=True)
class Drawing:
    """What one frame left for the next: the row the cursor's cell is laid on and the caret's mark, beside the row
    tops the frame itself drew.

    Attributes:
        cursor_row: The pattern row whose cell the cursor highlight stands on, or None for none.
        mark: The caret's mark as set for the next frame, or None while it is hidden.
        row_tops: The top edge of every frame row's slot, as the frame drew them.
    """

    cursor_row: Optional[int]
    mark: Optional[Rect]
    row_tops: Dict[int, float]

    def pitch(self) -> float:
        """How far apart two rows' tops stand."""
        tops = sorted(self.row_tops.values())
        return min(later - earlier for earlier, later in pairwise(tops))


def read_drawing(screen: Screen, channel: ChannelName, slot: SubColumn) -> Drawing:
    """Reads the drawing a frame left: the highlighted row and the mark for the next frame, the row tops of this one.
    Runs on the render thread.
    """
    rows = frame_rows()
    column = tracker_table_column(channel)
    cursor_row = None
    for place in screen.table_highlights():
        if place.table == TAG_SEQUENCER_TRACKER_TABLE and place.kind == HighlightKind.CELL and place.column == column:
            cursor_row = next((row for row, index in rows.items() if index == place.row), None)

    tops: Dict[int, float] = {}
    for row in rows:
        rect = read_item(tracker_cell(row, channel, slot)).rect
        if rect is not None:
            tops[row] = rect.y

    return Drawing(cursor_row=cursor_row, mark=caret_mark(), row_tops=tops)


def frames_apart(drawings: Sequence[Drawing]) -> List[Tuple[int, int, float, float]]:
    """Every frame that drew the caret's mark a row clear of the cursor's cell.

    A drawing's mark and cursor row are set for the frame after it, whose row tops the next drawing
    reports, so a mark is held against the next drawing's top of the row it was set for. Each entry
    names the frame's place in the run, the row, the row's top and the mark's top.
    """
    apart = []
    for index, (set_for_next, next_frame) in enumerate(pairwise(drawings)):
        if set_for_next.mark is None or set_for_next.cursor_row is None:
            continue

        top = next_frame.row_tops[set_for_next.cursor_row]
        if not top <= set_for_next.mark.y < top + next_frame.pitch():
            apart.append((index, set_for_next.cursor_row, top, set_for_next.mark.y))

    return apart


def glyph_runs(pixels: np.ndarray, cell: Rect, color: Sequence[float]) -> List[Tuple[int, int]]:
    """The stretches of pixel columns inside ``cell`` that carry ``color``, each a glyph, as (first, last) columns."""
    x0, y0 = int(cell.x), int(cell.y)
    x1, y1 = int(cell.x + cell.width), int(cell.y + cell.height)
    window = pixels[y0:y1, x0:x1, :RGB]
    distance = np.abs(window - np.asarray(color[:RGB])).max(axis=2)
    columns = np.flatnonzero((distance <= COLOR_TOLERANCE).any(axis=0))
    runs: List[Tuple[int, int]] = []
    for column in columns:
        absolute = x0 + int(column)
        if runs and absolute == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], absolute)
        else:
            runs.append((absolute, absolute))

    return runs


def glyph_bottom(pixels: np.ndarray, cell: Rect, color: Sequence[float]) -> int:
    """The lowest pixel row inside ``cell`` that carries ``color``."""
    x0, y0 = int(cell.x), int(cell.y)
    x1, y1 = int(cell.x + cell.width), int(cell.y + cell.height)
    window = pixels[y0:y1, x0:x1, :RGB]
    distance = np.abs(window - np.asarray(color[:RGB])).max(axis=2)
    rows = np.flatnonzero((distance <= COLOR_TOLERANCE).any(axis=1))
    return y0 + int(rows.max())
