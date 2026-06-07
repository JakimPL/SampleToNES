from __future__ import annotations

from typing import Dict, Final, Optional, Tuple

from pydantic.dataclasses import dataclass

from sampletones_application.ui.panels.sequencer.columns import COLUMNS, SUBCOLUMNS, flat_index, from_flat
from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.edit import ClearAction, EditAction
from sampletones_application.ui.panels.sequencer.input.subcolumn import SubColumn
from sampletones_core.constants.general import MAX_VOLUME

DIGIT_COUNT: Final[Dict[SubColumn, int]] = {
    SubColumn.INSTRUMENT: 2,
    SubColumn.TRANSPOSE: 2,
    SubColumn.VOLUME: 1,
}


def _parse(cursor: TrackerCursor, pending: str) -> Optional[EditAction]:
    try:
        match cursor.subcolumn:
            case SubColumn.INSTRUMENT:
                return EditAction(
                    row=cursor.row,
                    generator=cursor.generator,
                    sample_index=int(pending, 16),
                    transpose=None,
                    volume=None,
                )
            case SubColumn.VOLUME:
                return EditAction(
                    row=cursor.row,
                    generator=cursor.generator,
                    sample_index=None,
                    transpose=None,
                    volume=min(int(pending, 16), MAX_VOLUME),
                )
            case SubColumn.TRANSPOSE:
                return EditAction(
                    row=cursor.row,
                    generator=cursor.generator,
                    sample_index=None,
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
            cursor=TrackerCursor(
                new_row,
                self.cursor.generator,
                self.cursor.subcolumn,
            ),
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
            new_sub = SUBCOLUMNS[value % len(SUBCOLUMNS)]
            return TrackerInputState(
                cursor=TrackerCursor(
                    self.cursor.row,
                    self.cursor.generator,
                    new_sub,
                ),
                pending="",
            )

        current = flat_index(self.cursor.generator, self.cursor.subcolumn)
        return TrackerInputState(
            cursor=from_flat(self.cursor.row, current + value),
            pending="",
        )

    def navigate_column_by(self, delta: int) -> TrackerInputState:
        if self.cursor is None:
            return self

        current_idx = COLUMNS.index(self.cursor.generator)
        next_idx = (current_idx + delta) % len(COLUMNS)
        return TrackerInputState(
            cursor=TrackerCursor(self.cursor.row, COLUMNS[next_idx], SubColumn.INSTRUMENT),
            pending="",
        )

    def type_char(
        self,
        char: str,
    ) -> Tuple[TrackerInputState, Optional[EditAction]]:
        if self.cursor is None:
            return self, None

        pending = self.pending + char
        expected = DIGIT_COUNT[self.cursor.subcolumn]
        if len(pending) < expected:
            return TrackerInputState(cursor=self.cursor, pending=pending), None

        action = _parse(self.cursor, pending)
        return TrackerInputState(cursor=self.cursor, pending=""), action

    def commit_partial(self) -> Tuple[TrackerInputState, Optional[EditAction]]:
        if not self.pending or self.cursor is None:
            return self, None

        expected = DIGIT_COUNT[self.cursor.subcolumn]
        padded = self.pending.zfill(expected)
        action = _parse(self.cursor, padded)
        return TrackerInputState(cursor=self.cursor, pending=""), action

    def clear(self) -> Tuple[TrackerInputState, ClearAction]:
        action = ClearAction(
            row=self.cursor.row if self.cursor else 0,
            generator=self.cursor.generator if self.cursor else None,
        )
        return TrackerInputState(cursor=self.cursor, pending=""), action

    def cancel(self) -> TrackerInputState:
        return TrackerInputState(cursor=self.cursor, pending="")
