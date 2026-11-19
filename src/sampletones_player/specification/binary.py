from itertools import pairwise
from typing import Final

WORD_SIZE: Final[int] = 2
BYTE_VALUES: Final[int] = 256
MAX_BYTE_VALUE: Final[int] = BYTE_VALUES - 1
SIGNED_BYTE_LIMIT: Final[int] = BYTE_VALUES // 2


def signed_byte(value: int) -> int:
    """The number a byte states in two's complement, which is how a plane holds a signed value.

    Args:
        value: The byte as the stream holds it.

    Returns:
        int: The number it states.
    """
    if value < SIGNED_BYTE_LIMIT:
        return value

    return value - BYTE_VALUES


def unsigned_byte(value: int) -> int:
    """The byte a signed number reaches a stream as, which is the form a phrase shifts within.

    Args:
        value: The number to hold.

    Returns:
        int: The byte stating it.

    Raises:
        ValueError: If the number lies outside the range one byte states.
    """
    if not -SIGNED_BYTE_LIMIT <= value < SIGNED_BYTE_LIMIT:
        raise ValueError(f"a byte states {-SIGNED_BYTE_LIMIT} through {SIGNED_BYTE_LIMIT - 1}, and this is {value}")

    return value % BYTE_VALUES


def byte_steps(data: bytes) -> bytes:
    """The step from each byte to the next, wrapping around the byte's range.

    A run of steps is the shape a shift leaves alone, so a phrase and a plane are matched and
    counted by their steps. The steps are one fewer than the bytes.

    Args:
        data: The bytes read.

    Returns:
        bytes: One step per neighboring pair.
    """
    return bytes((following - value) % BYTE_VALUES for value, following in pairwise(data))
