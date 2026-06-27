from __future__ import annotations

from typing import Dict, Final, Optional, Tuple

from pydantic.dataclasses import dataclass

from sampletones_application.ui.panels.sequencer.columns import (
    COLUMNS,
    SUBCOLUMNS,
    flat_index,
    from_flat,
)
from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.edit import (
    ClearAction,
    EditAction,
)
from sampletones_application.ui.panels.sequencer.input.subcolumn import SubColumn
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_shared.constants.symbols import MINUS, PLUS, PLUS_MINUS, SIGNS

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
                sign = -1 if pending.startswith(MINUS) else 1
                magnitude = pending.lstrip(PLUS_MINUS)
                if not magnitude:
                    return None

                return EditAction(
                    row=cursor.row,
                    generator=cursor.generator,
                    sample_index=None,
                    transpose=sign * int(magnitude, 16),
                    volume=None,
                )
    except ValueError:
        return None


@dataclass
class TrackerInputState:
    cursor: Optional[TrackerCursor] = None
    pending: str = ""

    def reset_pending(self) -> TrackerInputState:
        return TrackerInputState(cursor=self.cursor, pending="")

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

        if self.cursor.subcolumn is SubColumn.INSTRUMENT and char == MINUS:
            return self.reset_pending(), self._note_off_action(self.cursor)

        if self.cursor.subcolumn is SubColumn.TRANSPOSE:
            return self._type_transpose_char(char)

        if char in SIGNS:
            return self, None

        pending = self.pending + char
        expected = DIGIT_COUNT[self.cursor.subcolumn]
        if len(pending) < expected:
            return TrackerInputState(cursor=self.cursor, pending=pending), None

        action = _parse(self.cursor, pending)
        return self.reset_pending(), action

    def _note_off_action(self, cursor: TrackerCursor) -> EditAction:
        return EditAction(
            row=cursor.row,
            generator=cursor.generator,
            sample_index=None,
            transpose=None,
            volume=None,
            note_off=True,
        )

    def _type_transpose_char(
        self,
        char: str,
    ) -> Tuple[TrackerInputState, Optional[EditAction]]:
        """Drives the signed transpose field: ``[±][H][H]``.

        The first slot is reserved for the sign. A leading sign sets it; a leading
        digit implies ``+``. A sign key pressed later flips the sign in place,
        keeping any digits already entered. The field commits once both magnitude
        digits are in.
        """
        if self.cursor is None:
            return self, None

        is_sign = char in SIGNS
        if not self.pending:
            pending = char if is_sign else f"{PLUS}{char}"
        elif is_sign:
            pending = char + self.pending[1:]
            return (
                TrackerInputState(cursor=self.cursor, pending=pending),
                None,
            )
        else:
            pending = self.pending + char

        digits = len(pending) - 1
        if digits < DIGIT_COUNT[SubColumn.TRANSPOSE]:
            return TrackerInputState(cursor=self.cursor, pending=pending), None

        action = _parse(self.cursor, pending)
        return self.reset_pending(), action

    def commit_partial(self) -> Tuple[TrackerInputState, Optional[EditAction]]:
        if not self.pending or self.cursor is None:
            return self, None

        if self.cursor.subcolumn is SubColumn.TRANSPOSE:
            action = _parse(self.cursor, self.pending)
            return self.reset_pending(), action

        expected = DIGIT_COUNT[self.cursor.subcolumn]
        padded = self.pending.zfill(expected)
        action = _parse(self.cursor, padded)
        return self.reset_pending(), action

    def clear(self) -> Tuple[TrackerInputState, ClearAction]:
        action = ClearAction(
            row=self.cursor.row if self.cursor else 0,
            generator=self.cursor.generator if self.cursor else None,
        )
        return self.reset_pending(), action

    def clear_subcolumn(self) -> Tuple[TrackerInputState, ClearAction]:
        action = ClearAction(
            row=self.cursor.row if self.cursor else 0,
            generator=self.cursor.generator if self.cursor else None,
            subcolumn=self.cursor.subcolumn if self.cursor else None,
        )
        return self.reset_pending(), action

    def cancel(self) -> TrackerInputState:
        return self.reset_pending()
