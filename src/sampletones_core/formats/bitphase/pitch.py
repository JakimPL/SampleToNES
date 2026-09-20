from sampletones_core.formats.bitphase.specification.chip import (
    MAX_TUNING_PERIOD,
    MIN_TUNING_PERIOD,
)
from sampletones_core.formats.bitphase.specification.instruments import MAX_TONE_ADD, MIN_TONE_ADD
from sampletones_core.formats.bitphase.specification.patterns import MAX_NOTE_INDEX, MIN_NOTE_INDEX
from sampletones_core.formats.bitphase.tuning import DEFAULT_TUNING_TABLE


def contour_period(base_index: int, step: int) -> int:
    """The period the note a contour step moves to sounds at.

    Args:
        base_index: Note index the slice was reconstructed at.
        step: Semitones the contour moves the note by.

    Returns:
        int: The period of the note the step reaches, held inside the tuning table.
    """
    index = min(max(base_index + step, MIN_NOTE_INDEX), MAX_NOTE_INDEX)
    return DEFAULT_TUNING_TABLE[index]


def sounding_offset(base_period: int, offset: int) -> int:
    """The tone offset that bends a period by as much as the channel goes on sounding.

    Bitphase adds the offset to the period its note resolves to, and a channel sounds while
    that sum stands within the timer's range, so the offset is held to what keeps it there.
    This is the rule ``bent_timer`` states for a divider, read in the periods Bitphase counts.

    Args:
        base_period: The period the tick's note resolves to.
        offset: The timer steps the tick stands away from that note.

    Returns:
        int: The offset to write, within both the timer's range and the field's own.
    """
    period = min(max(base_period + offset, MIN_TUNING_PERIOD), MAX_TUNING_PERIOD)
    return min(max(period - base_period, MIN_TONE_ADD), MAX_TONE_ADD)
