from __future__ import annotations

from typing import Dict, Final, Optional, Tuple

from pydantic.dataclasses import dataclass

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.edit import (
    ClearAction,
    EditAction,
)
from sampletones_application.view_model.sequencer.region import TrackerRegion
from sampletones_application.view_model.sequencer.slot import (
    SLOT_COUNT,
    SUBCOLUMNS,
    TrackerSlot,
    slot_from_flat,
)
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
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
    """Edit cursor, pending entry and selection anchor for the tracker grid.

    The anchor is where a range selection was started; the cursor is its other end, so the two
    together are the region a block operation acts on. Every plain move builds a state without
    one, which is what makes a move collapse a selection to the cell it lands in.
    """

    cursor: Optional[TrackerCursor] = None
    pending: str = ""
    anchor: Optional[TrackerCursor] = None

    def reset_pending(self) -> TrackerInputState:
        """Drops a partial entry, leaving the cursor and any selection where they stand.

        The anchor survives because this runs before every move, the extending ones included:
        each gesture then decides whether to hold the selection or collapse it.
        """
        return TrackerInputState(cursor=self.cursor, pending="", anchor=self.anchor)

    def collapse(self) -> TrackerInputState:
        """Drops the selection, leaving the cursor's own cell as the whole target."""
        return TrackerInputState(cursor=self.cursor, pending=self.pending)

    @property
    def region(self) -> Optional[TrackerRegion]:
        """The block a selection covers, once one has been started."""
        if self.cursor is None or self.anchor is None:
            return None

        anchor_slot = TrackerSlot(self.anchor.generator, self.anchor.subcolumn).flat_index
        cursor_slot = TrackerSlot(self.cursor.generator, self.cursor.subcolumn).flat_index
        return TrackerRegion(
            first_row=min(self.anchor.row, self.cursor.row),
            last_row=max(self.anchor.row, self.cursor.row),
            first_slot=min(anchor_slot, cursor_slot),
            last_slot=max(anchor_slot, cursor_slot),
        )

    def region_at(self, cell: TrackerCursor) -> TrackerRegion:
        """The block a gesture raised on ``cell`` acts on: the selection it stands in, or the cell
        alone.

        A gesture raised inside a selection acts on the whole of it, which is what a reader who has
        just dragged a range out expects it to reach; one raised anywhere else acts on the cell it
        names, which is a block of exactly that cell.
        """
        slot = TrackerSlot(cell.generator, cell.subcolumn)
        region = self.region
        if region is not None and region.covers(cell.row, slot):
            return region

        return TrackerRegion(
            first_row=cell.row,
            last_row=cell.row,
            first_slot=slot.flat_index,
            last_slot=slot.flat_index,
        )

    @property
    def target_region(self) -> Optional[TrackerRegion]:
        """The region a block gesture acts on: the selection, or the cursor's own cell.

        A cursor with nothing selected stands on a block of one cell, so copying reaches the cell
        the reader is working in and needs no selection made first.
        """
        if self.cursor is None:
            return None

        return self.region_at(self.cursor)

    def extend_to(self, cursor: TrackerCursor) -> TrackerInputState:
        """Carries the moving end of the selection to ``cursor``, anchoring it where it began.

        A selection that has not been started yet takes the cell the cursor stands on as its
        anchor, so the first extending gesture selects the cell it came from as well as the one
        it reaches.
        """
        return TrackerInputState(
            cursor=cursor,
            pending="",
            anchor=self.anchor if self.anchor is not None else self.cursor,
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

        current = TrackerSlot(self.cursor.generator, self.cursor.subcolumn).flat_index
        slot = slot_from_flat(max(0, min(current + value, SLOT_COUNT - 1)))
        return self.extend_to(TrackerCursor(self.cursor.row, slot.generator, slot.subcolumn))

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

        current = TrackerSlot(self.cursor.generator, self.cursor.subcolumn).flat_index
        slot = slot_from_flat((current + value) % SLOT_COUNT)
        return TrackerInputState(
            cursor=TrackerCursor(self.cursor.row, slot.generator, slot.subcolumn),
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

    def _after_entry(self) -> TrackerInputState:
        """The state a committed entry leaves: the cursor alone, nothing pending and nothing selected.

        Typing writes the one cell the cursor stands on, so it takes the selection down to that
        cell instead of leaving a range for the next gesture to act on.
        """
        return self.collapse().reset_pending()

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

    def cancel(self) -> TrackerInputState:
        """Drops a partial entry and any selection, which is what Escape asks of the grid."""
        return self.collapse().reset_pending()
