from typing import Callable, List, Sequence, Tuple

import numpy as np

from sampletones_core.instructions import TonalInstruction


def center_pitch(
    initial_pitch: int,
    pitches: List[int],
) -> int:
    """
    Picks the pitch at the midpoint of a contour's range.

    Measuring a contour's offsets from the midpoint of its ``(min, max)`` range keeps an
    arpeggio's relative steps small and straddling zero around one center pitch. An empty
    contour keeps the reference where it is.

    Args:
        initial_pitch: Reference pitch the offsets are measured against.
        pitches: Absolute pitches the contour covers.

    Returns:
        The center pitch: ``initial_pitch`` plus the midpoint of the offsets' range.
    """
    if not pitches:
        return initial_pitch

    differences = [pitch - initial_pitch for pitch in pitches]
    array = np.array(differences, dtype=np.int8)
    max_value = np.max(array)
    min_value = np.min(array)
    mean_value = (max_value + min_value) // 2
    return int(initial_pitch + mean_value)


def held_across_rests(
    instructions: Sequence[TonalInstruction],
    read: Callable[[TonalInstruction], int],
    default: int,
) -> Tuple[int, ...]:
    """One value per frame, holding what the last sounding frame stated across the rests.

    A rest states no pitch of its own, so the value a channel carries through it is the one it
    last sounded; the rests before the first sounding frame take that frame's value, so a
    dimension reads the same however a recording opens. This is the rule ``extract_data`` reads a
    contour by, stated once for every dimension a note carries.

    Args:
        instructions: The channel's per-frame instructions.
        read: What the dimension takes from one sounding frame.
        default: The value a channel that never sounds carries.

    Returns:
        Tuple[int, ...]: One value per instruction.
    """
    values: List[int] = []
    opening: int = default
    seen = False

    for instruction in instructions:
        if instruction.on:
            opening = read(instruction)
            if not seen:
                seen = True
                values = [opening for _ in values]

        values.append(opening)

    return tuple(values)
