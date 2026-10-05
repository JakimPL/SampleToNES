from typing import Sequence

from sampletones_core.formats.bitphase.specification.chip import PERIOD_OVER_TIMER
from sampletones_core.formats.bitphase.specification.instruments import MAX_TONE_ADD, MIN_TONE_ADD
from sampletones_core.formats.bitphase.specification.patterns import MAX_NOTE_INDEX, MIN_NOTE_INDEX
from sampletones_core.timers.arithmetic import bent_timer
from sampletones_shared.utils.arrays import clamp


def contour_period(
    tuning_table: Sequence[int],
    base_index: int,
    step: int,
) -> int:
    """The period the note a contour step moves to sounds at.

    Args:
        tuning_table: The period the song gives each note index.
        base_index: Note index the slice was reconstructed at.
        step: Semitones the contour moves the note by.

    Returns:
        int: The period of the note the step reaches, held inside the tuning table.
    """
    index = min(max(base_index + step, MIN_NOTE_INDEX), MAX_NOTE_INDEX)
    return tuning_table[index]


def sounding_offset(base_period: int, offset: int) -> int:
    """The tone offset that bends a period by as much as the channel goes on sounding.

    Bitphase adds the offset to the period its note resolves to and loads the timer with that
    period less one, so the offset follows ``bent_timer`` on the timer the period stands for. The
    bent note then sounds the divider in-app playback sounds, the longest one the register holds
    included.

    Args:
        base_period: The period the tick's note resolves to.
        offset: The timer steps the tick stands away from that note.

    Returns:
        int: The offset to write, within both the timer's range and the field's own.
    """
    period = bent_timer(base_period - PERIOD_OVER_TIMER, offset) + PERIOD_OVER_TIMER
    return clamp(period - base_period, MIN_TONE_ADD, MAX_TONE_ADD)
