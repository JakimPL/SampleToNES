from typing import NamedTuple

from sampletones_player.specification.compression import (
    OPCODE_SIZE,
    PHRASE_COUNT_SIZE,
    PHRASE_ESCAPE_SIZE,
    PHRASE_ID_ESCAPE,
    TOKEN_OPERAND_MASK,
    TOKEN_TAG_MASK,
    TRANSPOSE_SIZE,
    TokenTag,
)


class TokenSpan(NamedTuple):
    """What one written token occupies in a stream and covers in the song.

    Both readings of a token stream ask this: the driver to know where the next opcode lies, and
    the writer to find the byte a loop re-enters the stream at. Neither needs the dictionary, so
    the two figures follow from the opcode and the bytes behind it alone.

    Attributes:
        size: The bytes the token takes.
        ticks: The ticks the token covers.
    """

    size: int
    ticks: int


def _phrase_span(data: bytes, position: int, *, transposed: bool) -> TokenSpan:
    named = data[position] & TOKEN_OPERAND_MASK
    escape = PHRASE_ESCAPE_SIZE if named == PHRASE_ID_ESCAPE else 0
    count = position + OPCODE_SIZE + escape
    shift = TRANSPOSE_SIZE if transposed else 0
    return TokenSpan(
        size=OPCODE_SIZE + escape + PHRASE_COUNT_SIZE + shift,
        ticks=data[count] + 1,
    )


def token_span(data: bytes, position: int) -> TokenSpan:
    """Reads the token written at ``position``, answering what it takes and what it covers.

    Args:
        data: The plane's token stream.
        position: The byte the token's opcode lies at.

    Returns:
        TokenSpan: The bytes the token takes and the ticks it covers.
    """
    operand = data[position] & TOKEN_OPERAND_MASK
    match TokenTag(data[position] & TOKEN_TAG_MASK):
        case TokenTag.HOLD:
            return TokenSpan(size=OPCODE_SIZE, ticks=operand + 1)
        case TokenTag.LITERAL:
            return TokenSpan(size=OPCODE_SIZE + operand + 1, ticks=operand + 1)
        case TokenTag.PHRASE:
            return _phrase_span(data, position, transposed=False)
        case TokenTag.TRANSPOSED_PHRASE:
            return _phrase_span(data, position, transposed=True)
