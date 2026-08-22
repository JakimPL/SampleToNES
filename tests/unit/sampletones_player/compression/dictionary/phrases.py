from typing import Tuple

from sampletones_player.compression.dictionary.phrase import Phrase

BODY_STRIDE: int = 0x100


def phrase(*values: int) -> Phrase:
    return Phrase(body=bytes(values))


def distinct(count: int) -> Tuple[Phrase, ...]:
    return tuple(phrase(value % BODY_STRIDE, value // BODY_STRIDE) for value in range(count))
