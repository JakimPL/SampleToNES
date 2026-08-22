from functools import lru_cache

from sampletones_player.specification.compression import BYTE_VALUES


@lru_cache(maxsize=BYTE_VALUES)
def translation(transpose: int) -> bytes:
    """The byte table playing a phrase at a shift, every value moved by ``transpose``.

    A shift wraps within the byte, which is the one addition the driver performs and the one the
    encoder has to agree with. The tables are kept as they are asked for, since a song reaches
    for the same handful of shifts across every plane.

    Args:
        transpose: The shift every byte of a phrase is played at.

    Returns:
        bytes: The translation table the shift is applied through.
    """
    return bytes.maketrans(
        bytes(range(BYTE_VALUES)),
        bytes((value + transpose) % BYTE_VALUES for value in range(BYTE_VALUES)),
    )
