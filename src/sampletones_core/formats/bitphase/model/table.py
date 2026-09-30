from __future__ import annotations

from typing import Tuple

from pydantic import BaseModel, Field

from sampletones_core.formats.bitphase.model.config import BITPHASE_MODEL_CONFIG
from sampletones_core.formats.bitphase.specification.instruments import (
    ABSOLUTE_TABLE,
    FIRST_TABLE_STEP,
    LOOP_FROM_START,
    MAX_TABLE_ID,
    MIN_TABLE_ID,
)


class BitphaseTable(BaseModel):
    """A list of one value per step, whose meaning the column or effect reading it fixes.

    A pattern's table column reads it as a semitone contour, adding ``rows[position]`` to
    the channel's note and advancing a row every tick, so a table carries the pitch movement
    a reconstruction's arpeggio envelope describes. A speed effect reads it as tick counts,
    advancing a row every pattern line, so a table carries a song's groove.

    Playback returns to ``loop`` once it runs off the end, whichever column drives it.
    """

    model_config = BITPHASE_MODEL_CONFIG

    id: int = Field(
        ...,
        ge=MIN_TABLE_ID,
        le=MAX_TABLE_ID,
        description="Identifier a pattern's table column names.",
    )
    rows: Tuple[int, ...] = Field(
        ...,
        description="Value applied on each step.",
    )
    loop: int = Field(
        default=LOOP_FROM_START,
        ge=0,
        description="Row playback returns to after the last row.",
    )
    name: str = Field(
        ...,
        description="Name shown in the table list.",
    )
    additive: bool = Field(
        default=ABSOLUTE_TABLE,
        description="Whether each step adds to the value the table has reached, rather than to the note.",
    )

    @property
    def circling_step(self) -> int:
        """The step playback returns to past the last one, which is the first where ``loop`` stands outside the steps.

        Read from ``processTables`` of Bitphase's ``tracker-pattern-processor.js``, which takes ``loop``
        only where it stands above the first step and below the length.
        """
        if FIRST_TABLE_STEP < self.loop < len(self.rows):
            return self.loop

        return FIRST_TABLE_STEP

    def position_at(self, tick: int) -> int:
        """The step playback stands at ``tick`` ticks after the table started, one step per tick.

        Args:
            tick: Ticks since the table started, at least zero.

        Returns:
            int: The step playback reads on that tick.
        """
        length = len(self.rows)
        if tick < length:
            return tick

        start = self.circling_step
        return start + (tick - length) % (length - start)

    def moved(
        self,
        *,
        table_id: int,
        shift: int,
        start: int,
        name: str,
    ) -> BitphaseTable:
        """This table with every step moved by ``shift``, playing from the step ``start`` on.

        A table starting at a later step lays the steps from there first, then circles over the
        steps this one circles over, so it plays what this one plays from ``start`` on.

        Args:
            table_id: The identifier the new table takes.
            shift: The semitones every step moves by.
            start: The step of this table the new one opens on.
            name: The name the new table is listed by.

        Returns:
            BitphaseTable: The moved table.
        """
        rows = tuple(step + shift for step in self.rows)
        circling = self.circling_step
        if start >= circling:
            laid = rows[start:] + rows[circling:start]
            loop = LOOP_FROM_START
        else:
            laid = rows[start:]
            loop = circling - start

        return BitphaseTable(
            id=table_id,
            rows=laid,
            loop=loop,
            name=name,
            additive=self.additive,
        )
