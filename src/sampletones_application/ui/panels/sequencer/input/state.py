from __future__ import annotations

from typing import Dict, Final, Optional, Tuple

from pydantic.dataclasses import dataclass

from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.edit import ClearAction, EditAction
from sampletones_application.ui.panels.sequencer.input.subcolumn import SubColumns
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.constants.general import MAX_VOLUME

_COLUMNS: Final[Tuple[Optional[GeneratorName], ...]] = (None,) + tuple(GeneratorName.items())
_SUBCOLUMNS: Final[Tuple[SubColumns, ...]] = tuple(SubColumns)
_DIGIT_COUNT: Final[Dict[SubColumns, int]] = {
    SubColumns.INSTRUMENT: 2,
    SubColumns.TRANSPOSE: 2,
    SubColumns.VOLUME: 1,
}


def _flat_index(generator: Optional[GeneratorName], subcolumn: SubColumns) -> int:
    return _COLUMNS.index(generator) * len(_SUBCOLUMNS) + _SUBCOLUMNS.index(subcolumn)


def _from_flat(row: int, index: int) -> TrackerCursor:
    index %= len(_COLUMNS) * len(_SUBCOLUMNS)
    col, sub = divmod(index, len(_SUBCOLUMNS))
    return TrackerCursor(row, _COLUMNS[col], _SUBCOLUMNS[sub])


def _parse(cursor: TrackerCursor, pending: str) -> Optional[EditAction]:
    try:
        match cursor.subcolumn:
            case SubColumns.INSTRUMENT:
                return EditAction(
                    row=cursor.row,
                    generator=cursor.generator,
                    sample_idex=int(pending, 16),
                    transpose=None,
                    volume=None,
                )
            case SubColumns.VOLUME:
                return EditAction(
                    row=cursor.row,
                    generator=cursor.generator,
                    sample_idex=None,
                    transpose=None,
                    volume=min(int(pending, 16), MAX_VOLUME),
                )
            case SubColumns.TRANSPOSE:
                return EditAction(
                    row=cursor.row,
                    generator=cursor.generator,
                    sample_idex=None,
                    transpose=int(pending, 16),
                    volume=None,
                )
    except ValueError:
        return None


@dataclass
class TrackerInputState:
    cursor: Optional[TrackerCursor] = None
    pending: str = ""

    def navigate_row(
        self,
        value: int,
        row_count: int,
        absolute: bool = False,
    ) -> TrackerInputState:
        if self.cursor is None or row_count == 0:
            return self
        new_row = value if absolute else self.cursor.row + value
        new_row = max(0, min(new_row, row_count - 1))
        return TrackerInputState(
            cursor=TrackerCursor(new_row, self.cursor.generator, self.cursor.subcolumn),
            pending="",
        )

    def navigate_subcolumn(
        self,
        value: int,
        absolute: bool = False,
    ) -> TrackerInputState:
        if self.cursor is None:
            return self
        if absolute:
            new_sub = _SUBCOLUMNS[value % len(_SUBCOLUMNS)]
            return TrackerInputState(
                cursor=TrackerCursor(self.cursor.row, self.cursor.generator, new_sub),
                pending="",
            )
        current = _flat_index(self.cursor.generator, self.cursor.subcolumn)
        return TrackerInputState(cursor=_from_flat(self.cursor.row, current + value), pending="")

    def navigate_column(
        self,
        column: Optional[GeneratorName],
    ) -> TrackerInputState:
        if self.cursor is None:
            return self
        return TrackerInputState(
            cursor=TrackerCursor(self.cursor.row, column, SubColumns.INSTRUMENT),
            pending="",
        )

    def type_char(
        self,
        char: str,
    ) -> Tuple[TrackerInputState, Optional[EditAction]]:
        if self.cursor is None:
            return self, None
        pending = self.pending + char
        expected = _DIGIT_COUNT[self.cursor.subcolumn]
        if len(pending) < expected:
            return TrackerInputState(cursor=self.cursor, pending=pending), None
        action = _parse(self.cursor, pending)
        return TrackerInputState(cursor=self.cursor, pending=""), action

    def clear(self) -> Tuple[TrackerInputState, ClearAction]:
        action = ClearAction(
            row=self.cursor.row if self.cursor else 0,
            generator=self.cursor.generator if self.cursor else None,
        )
        return TrackerInputState(cursor=self.cursor, pending=""), action

    def cancel(self) -> TrackerInputState:
        return TrackerInputState(cursor=self.cursor, pending="")
