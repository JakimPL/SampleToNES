from __future__ import annotations

from functools import cached_property
from typing import Final, Tuple

from pydantic import BaseModel, ConfigDict

from sampletones_core.timers.nearest import NearestPitch, nearest_pitches
from sampletones_core.timers.utils import get_timer_table
from sampletones_player.specification.registers import (
    MAX_REGISTER_VALUE,
    TIMER_HIGH_SHIFT,
)
from sampletones_shared.constants.music import LIMIT_MAX_PITCH, LIMIT_MIN_PITCH
from sampletones_shared.music import Tuning

PITCH_COUNT: Final[int] = LIMIT_MAX_PITCH - LIMIT_MIN_PITCH + 1


class PitchTable(BaseModel):
    """The timer every pitch sounds at, indexed the way a channel's plane names a pitch.

    A plane states a pitch as its distance above the lowest pitch the project reaches, and the
    table resolves that index into the divider the hardware takes. Naming pitches rather than
    dividers is what makes a phrase transposable: adding a semitone to an index moves a note,
    where adding one to a timer means nothing.

    Attributes:
        timers: The timer for each pitch, from the lowest the project reaches upward.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    timers: Tuple[int, ...]

    @classmethod
    def from_tuning(cls, tuning: Tuning) -> PitchTable:
        """Builds the table the reconstruction's own generators are tuned by.

        Args:
            tuning: Where concert pitch sits for the song being written.

        Returns:
            PitchTable: The timer each pitch sounds at, in pitch order.
        """
        table = get_timer_table(tuning)
        return cls(
            timers=tuple(
                table[pitch]
                for pitch in range(
                    LIMIT_MIN_PITCH,
                    LIMIT_MAX_PITCH + 1,
                )
            )
        )

    @cached_property
    def nearest(self) -> Tuple[NearestPitch, ...]:
        """The index lying nearest every divider the register holds, beside the steps between them.

        A tone channel's planes carry each tick's divider as this index and a bend of the steps
        left over, which the driver adds back. Within the table's span the steps stay within half
        the widest gap between neighboring pitches, well inside the signed byte a bend plane holds.
        Pitches beyond the divider's range share the timer they are clamped to, and they sound
        alike, so the lowest index stands for the whole group.
        """
        return nearest_pitches(dict(enumerate(self.timers)))

    @property
    def data(self) -> bytes:
        """The table as the driver reads it: every low byte, then every high byte."""
        low = bytes(timer & MAX_REGISTER_VALUE for timer in self.timers)
        high = bytes(timer >> TIMER_HIGH_SHIFT for timer in self.timers)
        return low + high
