from __future__ import annotations

from typing import Dict, Final, Tuple

from pydantic import BaseModel, ConfigDict

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
        timers: The timer for each pitch, from the lowest the project reaches upwards.
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

    @property
    def indices(self) -> Dict[int, int]:
        """The index each timer is written as, the lowest pitch sounding it standing for it.

        Pitches beyond the divider's range share the timer they are clamped to, and they sound
        alike, so one index stands for the whole group and a stream naming any of them resolves
        back to the timer it was written from.
        """
        indices: Dict[int, int] = {}
        for index, timer in enumerate(self.timers):
            indices.setdefault(timer, index)

        return indices

    @property
    def data(self) -> bytes:
        """The table as the driver reads it: every low byte, then every high byte."""
        low = bytes(timer & MAX_REGISTER_VALUE for timer in self.timers)
        high = bytes(timer >> TIMER_HIGH_SHIFT for timer in self.timers)
        return low + high
