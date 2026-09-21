from typing import NamedTuple

from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.specification.compression import (
    DEFAULT_COUNT_FLAG,
    OPCODE_SIZE,
    PHRASE_COUNT_SIZE,
    PHRASE_ESCAPE_SIZE,
    PHRASE_ID_ESCAPE,
    PHRASE_ID_MASK,
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


def _phrase_span(
    data: bytes,
    position: int,
    table: PhraseTable,
    *,
    transposed: bool,
) -> TokenSpan:
    named = data[position] & PHRASE_ID_MASK
    stated = not data[position] & DEFAULT_COUNT_FLAG
    escape = PHRASE_ESCAPE_SIZE if named == PHRASE_ID_ESCAPE else 0
    after = position + OPCODE_SIZE + escape
    phrase_id = data[position + OPCODE_SIZE] if escape else named
    shift = TRANSPOSE_SIZE if transposed else 0
    return TokenSpan(
        size=OPCODE_SIZE + escape + (PHRASE_COUNT_SIZE if stated else 0) + shift,
        ticks=data[after] + 1 if stated else table[phrase_id].default,
    )


def token_span(
    data: bytes,
    position: int,
    table: PhraseTable,
) -> TokenSpan:
    """Reads the token written at ``position``, answering what it takes and what it covers.

    Args:
        data: The plane's token stream.
        position: The byte the token's opcode lies at.
        table: The dictionary the tokens name, for the count a phrase carries.

    Returns:
        TokenSpan: The bytes the token takes and the values it covers.
    """
    operand = data[position] & TOKEN_OPERAND_MASK
    match TokenTag(data[position] & TOKEN_TAG_MASK):
        case TokenTag.HOLD:
            return TokenSpan(size=OPCODE_SIZE, ticks=operand + 1)
        case TokenTag.LITERAL:
            return TokenSpan(size=OPCODE_SIZE + operand + 1, ticks=operand + 1)
        case TokenTag.PHRASE:
            return _phrase_span(data, position, table, transposed=False)
        case TokenTag.TRANSPOSED_PHRASE:
            return _phrase_span(data, position, table, transposed=True)
