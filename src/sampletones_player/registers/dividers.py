from typing import Dict, Mapping, Sequence, Tuple

from sampletones_core.timers.arithmetic import bent_timer
from sampletones_core.timers.nearest import nearest_pitch
from sampletones_player.specification.binary import SIGNED_BYTE_LIMIT


def bent_dividers(
    pitches: Sequence[int],
    offsets: Sequence[int],
    timer_table: Dict[int, int],
) -> Tuple[int, ...]:
    """The divider each frame sounds: its note's own, moved by the bend the frame carries.

    This is the divider the generators render a frame at, so a tone channel's timer registers
    carry exactly what the sequencer sounds.

    Args:
        pitches: The note each frame names, held across rests.
        offsets: The timer steps each frame is bent by, held across rests the same way.
        timer_table: The timer register value each pitch sounds at.

    Returns:
        Tuple[int, ...]: One divider per frame.

    Raises:
        ValueError: If the notes and the bends cover different frames.
    """
    return tuple(bent_timer(timer_table[pitch], offset) for pitch, offset in zip(pitches, offsets, strict=True))


def anchored_pitches(
    pitches: Sequence[int],
    dividers: Sequence[int],
    timer_table: Mapping[int, int],
) -> Tuple[int, ...]:
    """The pitch each frame's divider is counted from, which the channel's value plane names.

    Counting a bend from the frame's own note keeps it the same bytes at every pitch a row
    transposes the note to, since a transpose moves the note and keeps the bend's steps. That is
    what lets one dictionary entry serve a bent sample at every transposition. A bend past the
    signed byte a bend plane holds is counted from the pitch lying nearest instead.

    Args:
        pitches: The note each frame names.
        dividers: The divider each frame sounds.
        timer_table: The timer register value each pitch sounds at.

    Returns:
        Tuple[int, ...]: One pitch per frame.

    Raises:
        ValueError: If the notes and the dividers cover different frames.
    """
    return tuple(_anchor(pitch, divider, timer_table) for pitch, divider in zip(pitches, dividers, strict=True))


def _anchor(
    pitch: int,
    divider: int,
    timer_table: Mapping[int, int],
) -> int:
    if -SIGNED_BYTE_LIMIT <= divider - timer_table[pitch] < SIGNED_BYTE_LIMIT:
        return pitch

    return nearest_pitch(timer_table, divider).pitch
