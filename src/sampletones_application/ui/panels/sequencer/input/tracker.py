from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Final, Optional, Tuple

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.ui.panels.sequencer.input.edit import (
    ClearAction,
    EditAction,
)
from sampletones_application.ui.panels.sequencer.input.state import GridInputState
from sampletones_application.view_model.sequencer.region import TrackerRegion
from sampletones_application.view_model.sequencer.slot import (
    SLOT_COUNT,
    SUBCOLUMNS,
    TrackerSlot,
    column_slot_base,
    slot_from_flat,
)
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_shared.constants.general import HEXADECIMAL_BASE
from sampletones_shared.constants.symbols import MINUS, PLUS, PLUS_MINUS, SIGNS

DIGIT_COUNT: Final[Dict[SubColumn, int]] = {
    SubColumn.INSTRUMENT: 2,
    SubColumn.TRANSPOSE: 2,
    SubColumn.VOLUME: 1,
}


@dataclass(frozen=True)
class TrackerCursor:
    row: int
    generator: Optional[GeneratorName]
    subcolumn: SubColumn


def _parse(cursor: TrackerCursor, pending: str) -> Optional[EditAction]:
    try:
        match cursor.subcolumn:
            case SubColumn.INSTRUMENT:
                return EditAction(
                    row=cursor.row,
                    generator=cursor.generator,
                    sample_index=int(pending, HEXADECIMAL_BASE),
                    transpose=None,
                    volume=None,
                )
            case SubColumn.VOLUME:
                return EditAction(
                    row=cursor.row,
                    generator=cursor.generator,
                    sample_index=None,
                    transpose=None,
                    volume=min(int(pending, HEXADECIMAL_BASE), MAX_VOLUME),
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
                    transpose=sign * int(magnitude, HEXADECIMAL_BASE),
                    volume=None,
                )
    except ValueError:
        return None


@dataclass(frozen=True)
class TrackerInputState(GridInputState[TrackerCursor, TrackerRegion]):
    """Edit cursor, pending entry and selection anchor for the tracker grid.

    A cell of the grid is a row crossed with a slot — a channel and one of its subcolumns —
    so a selection reaches across the sample column and the channels alike, and typing drives
    the subcolumn the cursor stands on.
    """

    def _region_between(
        self,
        first: TrackerCursor,
        second: TrackerCursor,
    ) -> TrackerRegion:
        first_slot = TrackerSlot(first.generator, first.subcolumn).flat_index
        second_slot = TrackerSlot(second.generator, second.subcolumn).flat_index
        return TrackerRegion(
            first_row=min(first.row, second.row),
            last_row=max(first.row, second.row),
            first_slot=min(first_slot, second_slot),
            last_slot=max(first_slot, second_slot),
        )

    def _covers(self, region: TrackerRegion, cell: TrackerCursor) -> bool:
        return region.covers(cell.row, TrackerSlot(cell.generator, cell.subcolumn))

    def select_all(self, row_count: int) -> TrackerInputState:
        """Selects the whole frame: every row of it, across every slot the axis lays out."""
        return self._select_slots(0, SLOT_COUNT - 1, row_count)

    def select_column(
        self,
        cell: TrackerCursor,
        row_count: int,
    ) -> TrackerInputState:
        """Selects the column ``cell`` stands in: every row of it, across that column's subcolumns.

        The sample column is an ordinary member of the axis here, so selecting it selects a column
        the way selecting a channel does.
        """
        base = column_slot_base(cell.generator)
        return self._select_slots(base, base + len(SUBCOLUMNS) - 1, row_count)

    def select_subcolumn(
        self,
        cell: TrackerCursor,
        row_count: int,
    ) -> TrackerInputState:
        """Selects the subcolumn ``cell`` stands in: every row of it, at that one slot."""
        slot = TrackerSlot(cell.generator, cell.subcolumn).flat_index
        return self._select_slots(slot, slot, row_count)

    def _select_slots(
        self,
        first_slot: int,
        last_slot: int,
        row_count: int,
    ) -> TrackerInputState:
        """Selects a run of slots down the whole frame, the cursor landing on its far corner."""
        if row_count == 0:
            return self

        first = slot_from_flat(first_slot)
        last = slot_from_flat(last_slot)
        return self.select_between(
            TrackerCursor(0, first.generator, first.subcolumn),
            TrackerCursor(row_count - 1, last.generator, last.subcolumn),
        )

    def extend_row(
        self,
        value: int,
        row_count: int,
        absolute: bool = False,
    ) -> TrackerInputState:
        """Carries the selection's moving end to another row of the same slot."""
        if self.cursor is None or row_count == 0:
            return self

        new_row = value if absolute else self.cursor.row + value
        new_row = max(0, min(new_row, row_count - 1))
        return self.extend_to(
            TrackerCursor(
                new_row,
                self.cursor.generator,
                self.cursor.subcolumn,
            )
        )

    def extend_slot(self, value: int) -> TrackerInputState:
        """Carries the selection's moving end along the flat slot axis, stopping at either end.

        A selection covers a run of the grid, so the walk stops at the first and the last slot
        rather than wrapping around the way plain navigation does.
        """
        if self.cursor is None:
            return self

        current = TrackerSlot(
            self.cursor.generator,
            self.cursor.subcolumn,
        ).flat_index
        slot = slot_from_flat(max(0, min(current + value, SLOT_COUNT - 1)))
        return self.extend_to(
            TrackerCursor(
                self.cursor.row,
                slot.generator,
                slot.subcolumn,
            )
        )

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
        """Steps the cursor along the flattened slot axis, wrapping at either end.

        Wrapping is a navigation policy the cursor owns: walking right off the last
        volume slot lands on the sample column's instrument, so a held arrow key
        tours the whole row.
        """
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

        current = TrackerSlot(
            self.cursor.generator,
            self.cursor.subcolumn,
        ).flat_index
        slot = slot_from_flat((current + value) % SLOT_COUNT)
        return TrackerInputState(
            cursor=TrackerCursor(
                self.cursor.row,
                slot.generator,
                slot.subcolumn,
            ),
            pending="",
        )

    def navigate_column_by(self, delta: int) -> TrackerInputState:
        if self.cursor is None:
            return self

        current_idx = CHANNEL_AXIS.index(self.cursor.generator)
        next_idx = (current_idx + delta) % len(CHANNEL_AXIS)
        return TrackerInputState(
            cursor=TrackerCursor(
                self.cursor.row,
                CHANNEL_AXIS[next_idx],
                self.cursor.subcolumn,
            ),
            pending="",
        )

    def type_char(
        self,
        char: str,
    ) -> Tuple[TrackerInputState, Optional[EditAction]]:
        if self.cursor is None:
            return self, None

        if self.cursor.subcolumn is SubColumn.INSTRUMENT and char == MINUS:
            return self._after_entry(), self._note_off_action(self.cursor)

        if self.cursor.subcolumn is SubColumn.TRANSPOSE:
            return self._type_transpose_char(char)

        if char in SIGNS:
            return self, None

        pending = self.pending + char
        expected = DIGIT_COUNT[self.cursor.subcolumn]
        if len(pending) < expected:
            return TrackerInputState(cursor=self.cursor, pending=pending), None

        action = _parse(self.cursor, pending)
        return self._after_entry(), action

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
        return self._after_entry(), action

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
