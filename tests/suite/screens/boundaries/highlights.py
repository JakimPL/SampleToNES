import threading
from dataclasses import dataclass
from enum import StrEnum
from typing import Dict, Final, Optional, Sequence, Tuple, Union

import dearpygui.dearpygui as dpg
import pytest

TableItem = Union[int, str]
Color = Tuple[float, ...]
WHOLE_LINE: Final[None] = None


class HighlightKind(StrEnum):
    """The stretch of a table one highlight covers."""

    ROW = "row"
    CELL = "cell"
    COLUMN = "column"


@dataclass(frozen=True)
class HighlightPlace:
    """Where a table highlight stands: the table, the stretch it covers, and the row and the column it covers.

    Attributes:
        table: The table's tag.
        kind: Whether the highlight covers a row, a cell or a column.
        row: The row it covers, or ``None`` for a column.
        column: The column it covers, or ``None`` for a row.
    """

    table: str
    kind: HighlightKind
    row: Optional[int]
    column: Optional[int]


class TableHighlights:
    """Notes every highlight the application lays on a table and lifts from one, with its color.

    DearPyGui holds a table's row, cell and column highlights as the table's own state, and answers
    whether one stands but never its color. The stand-in wraps the calls that lay and lift them,
    which run as they did, so the highlights standing and their colors are known as the
    application left them, from the first frame on.
    """

    def __init__(self) -> None:
        self._standing: Dict[HighlightPlace, Color] = {}
        self._lock = threading.Lock()

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Wraps DearPyGui's calls that lay and lift table highlights, so each one is noted as it runs."""
        lay_row = dpg.highlight_table_row
        lay_cell = dpg.highlight_table_cell
        lay_column = dpg.highlight_table_column
        lift_row = dpg.unhighlight_table_row
        lift_cell = dpg.unhighlight_table_cell
        lift_column = dpg.unhighlight_table_column

        def highlight_row(table: TableItem, row: int, color: Sequence[float]) -> None:
            lay_row(table, row, color)
            self._lay(_place(table, HighlightKind.ROW, row, WHOLE_LINE), color)

        def highlight_cell(table: TableItem, row: int, column: int, color: Sequence[float]) -> None:
            lay_cell(table, row, column, color)
            self._lay(_place(table, HighlightKind.CELL, row, column), color)

        def highlight_column(table: TableItem, column: int, color: Sequence[float]) -> None:
            lay_column(table, column, color)
            self._lay(_place(table, HighlightKind.COLUMN, WHOLE_LINE, column), color)

        def unhighlight_row(table: TableItem, row: int) -> None:
            lift_row(table, row)
            self._lift(_place(table, HighlightKind.ROW, row, WHOLE_LINE))

        def unhighlight_cell(table: TableItem, row: int, column: int) -> None:
            lift_cell(table, row, column)
            self._lift(_place(table, HighlightKind.CELL, row, column))

        def unhighlight_column(table: TableItem, column: int) -> None:
            lift_column(table, column)
            self._lift(_place(table, HighlightKind.COLUMN, WHOLE_LINE, column))

        monkeypatch.setattr(dpg, "highlight_table_row", highlight_row)
        monkeypatch.setattr(dpg, "highlight_table_cell", highlight_cell)
        monkeypatch.setattr(dpg, "highlight_table_column", highlight_column)
        monkeypatch.setattr(dpg, "unhighlight_table_row", unhighlight_row)
        monkeypatch.setattr(dpg, "unhighlight_table_cell", unhighlight_cell)
        monkeypatch.setattr(dpg, "unhighlight_table_column", unhighlight_column)

    def standing(self) -> Dict[HighlightPlace, Color]:
        """Every highlight standing, with the color it was laid in."""
        with self._lock:
            return dict(self._standing)

    def _lay(self, place: HighlightPlace, color: Sequence[float]) -> None:
        with self._lock:
            self._standing[place] = tuple(float(part) for part in color)

    def _lift(self, place: HighlightPlace) -> None:
        with self._lock:
            self._standing.pop(place, None)


def _place(
    table: TableItem,
    kind: HighlightKind,
    row: Optional[int],
    column: Optional[int],
) -> HighlightPlace:
    """The place a call names, its table known by its tag. Runs on the render thread."""
    return HighlightPlace(table=str(dpg.get_item_alias(table) or table), kind=kind, row=row, column=column)
