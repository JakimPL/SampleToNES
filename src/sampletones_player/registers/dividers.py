from typing import Dict, Sequence, Tuple

from sampletones_core.timers.arithmetic import bent_timer


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
