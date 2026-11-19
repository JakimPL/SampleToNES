from typing import Sequence, TypeVar

HeldT = TypeVar("HeldT")


def hold(values: Sequence[HeldT], index: int) -> HeldT:
    """Reads a held stream at a position, sustaining its final value past the stream's end.

    A stream states a value for every position it covers and holds its last one over every
    position beyond them: an exporter appends one silent tick past a channel's instructions, a
    channel that runs out early carries its last values through the rest of a song, and a phrase
    played past its end holds its final value onward.

    Args:
        values: The held stream.
        index: The position to read, counted from the stream's start.

    Returns:
        HeldT: The value at that position, or the stream's final value once the index reaches
            its end.

    Raises:
        ValueError: If the stream is empty or the index is negative.
    """
    if len(values) == 0:
        raise ValueError("an empty stream holds no value to read")

    if index < 0:
        raise ValueError(f"a stream is read from its start, and the index is {index}")

    return values[min(index, len(values) - 1)]
