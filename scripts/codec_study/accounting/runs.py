from itertools import groupby
from typing import Tuple

from sampletones_player.specification.binary import BYTE_VALUES


def runs(data: bytes) -> Tuple[int, ...]:
    """The lengths of the runs of one value ``data`` is made of, in order.

    Args:
        data: The bytes to read.

    Returns:
        Tuple[int, ...]: One length per run; they sum to the length of ``data``.
    """
    return tuple(len(list(group)) for _, group in groupby(data))


def ramps(data: bytes) -> Tuple[int, ...]:
    """The lengths of the constant-step runs ``data`` is made of, steps of zero left aside.

    A ramp is a series stepping by the same amount from one value to the next, a fade or a
    slide, and its length counts the values it covers.

    Args:
        data: The bytes to read.

    Returns:
        Tuple[int, ...]: The length of every ramp of at least two values.
    """
    steps = tuple((following - value) % BYTE_VALUES for value, following in zip(data, data[1:]))
    return tuple(len(list(group)) + 1 for step, group in groupby(steps) if step != 0)
