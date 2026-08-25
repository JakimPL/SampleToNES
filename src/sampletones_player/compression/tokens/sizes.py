from sampletones_player.specification.compression import (
    OPCODE_SIZE,
    PHRASE_COUNT_SIZE,
    PHRASE_ESCAPE_SIZE,
    PHRASE_ID_ESCAPE,
    TRANSPOSE_SIZE,
)


def hold_size() -> int:
    """The bytes a hold takes, its opcode carrying the count."""
    return OPCODE_SIZE


def literal_size(length: int) -> int:
    """The bytes a literal of ``length`` values takes, its opcode carrying the length."""
    return OPCODE_SIZE + length


def phrase_size(phrase_id: int, transpose: int) -> int:
    """The bytes a phrase token takes.

    The opcode carries the phrase's id where the id is one of the cheap ones, and a further byte
    names it beyond those. A count byte follows, and a shifted phrase carries the shift as well.

    Args:
        phrase_id: Position the phrase takes in the table.
        transpose: The shift every byte of the phrase is played at.

    Returns:
        int: The bytes the token takes.
    """
    escape = PHRASE_ESCAPE_SIZE if phrase_id >= PHRASE_ID_ESCAPE else 0
    shift = TRANSPOSE_SIZE if transpose else 0
    return OPCODE_SIZE + PHRASE_COUNT_SIZE + escape + shift
