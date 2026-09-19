from typing import List, Sequence, Tuple

from sampletones_player.specification.compression import BEND_FLAG, PITCH_INDEX_MASK


def is_flagged(value: int) -> bool:
    """Whether a tone channel's value byte carries a bend, read from the channel's bend plane.

    Args:
        value: The value byte.

    Returns:
        bool: Whether the tick reads its bend from the bend plane.
    """
    return bool(value & BEND_FLAG)


def pitch_index(value: int) -> int:
    """The pitch index a tone channel's value byte names, whatever its flag says.

    Args:
        value: The value byte.

    Returns:
        int: The index into the pitch table.
    """
    return value & PITCH_INDEX_MASK


def flagged_value(index: int, flag: bool) -> int:
    """The value byte naming a pitch index, flagged where the tick carries a bend.

    Args:
        index: The index into the pitch table.
        flag: Whether the tick reads its bend from the bend plane.

    Returns:
        int: The value byte.

    Raises:
        ValueError: If the index reaches the flag's bit.
    """
    if index & ~PITCH_INDEX_MASK:
        raise ValueError(f"a value byte names indices up to {PITCH_INDEX_MASK}, and this is {index}")

    return index | BEND_FLAG if flag else index


def flagged_ticks(value: bytes) -> int:
    """The ticks of a tone channel carrying a bend, which is how many values its bend plane holds.

    Args:
        value: The channel's value plane.

    Returns:
        int: The flagged ticks.
    """
    return sum(1 for byte in value if is_flagged(byte))


def note_flags(
    indices: Sequence[int],
    offsets: Sequence[int],
) -> Tuple[bool, ...]:
    """Which ticks of a tone channel carry a bend: each note from its first bent tick to its last.

    A note is a run of ticks naming one pitch. Flagging it whole between its bends keeps the
    value plane still while a bend passes through zero, as a vibrato does, and a note that never
    bends carries no flag at all, so its bend plane holds nothing for it.

    Args:
        indices: The pitch index each tick names.
        offsets: The divider steps each tick stands away from its pitch.

    Returns:
        Tuple[bool, ...]: One flag per tick.

    Raises:
        ValueError: If the indices and the offsets cover different ticks.
    """
    if len(indices) != len(offsets):
        raise ValueError(
            f"a flag reads an index and an offset per tick, and these cover {len(indices)} and {len(offsets)}"
        )

    flags: List[bool] = [False] * len(indices)
    start = 0
    for end in range(1, len(indices) + 1):
        if end < len(indices) and indices[end] == indices[start]:
            continue

        bent = [tick for tick in range(start, end) if offsets[tick] != 0]
        if bent:
            flags[bent[0] : bent[-1] + 1] = [True] * (bent[-1] - bent[0] + 1)

        start = end

    return tuple(flags)
