from typing import Sequence, TypeVar

HeldValue = TypeVar("HeldValue")


def hold(values: Sequence[HeldValue], index: int) -> HeldValue:
    """Reads a held stream at a tick, sustaining its final value past the stream's end.

    An exporter states a channel's pitch and timbre for every tick its instructions cover, and
    appends one silent tick past them so a sample ends quiet. That release tick reads the values
    the channel was holding when it stopped sounding, and the same rule carries a channel that
    runs out early through the rest of a song.

    Args:
        values: The held stream, covering at least one tick.
        index: The tick to read.

    Returns:
        HeldValue: The value at that tick, or the stream's final value once the index reaches
            its end.
    """
    return values[min(index, len(values) - 1)]
