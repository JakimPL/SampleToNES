from typing import List, NamedTuple, Optional, Tuple

from sampletones_player.compression.tokens.span import token_span
from sampletones_player.specification.compression import (
    OPCODE_SIZE,
    PHRASE_COUNT_SIZE,
    PHRASE_ESCAPE_SIZE,
    PHRASE_ID_ESCAPE,
    TOKEN_OPERAND_MASK,
    TOKEN_TAG_MASK,
    TokenTag,
)


class ReadToken(NamedTuple):
    """One token read back from a written stream, with everything the accounting asks of it.

    Attributes:
        tag: What kind of token it is.
        tick: The tick the token starts on.
        size: The bytes the token takes.
        ticks: The ticks the token covers.
        payload: The values a literal carries, empty for every other kind.
        phrase_id: The phrase a phrase token names, ``None`` for every other kind.
        transpose: The shift a transposed phrase is played at, zero otherwise.
    """

    tag: TokenTag
    tick: int
    size: int
    ticks: int
    payload: bytes
    phrase_id: Optional[int]
    transpose: int

    @property
    def names_a_phrase(self) -> bool:
        """Whether the token plays a phrase from the dictionary."""
        return self.phrase_id is not None


def _phrase_operands(
    stream: bytes,
    position: int,
    operand: int,
    *,
    transposed: bool,
) -> Tuple[int, int]:
    after = position + OPCODE_SIZE
    phrase_id = operand
    if operand == PHRASE_ID_ESCAPE:
        phrase_id = stream[after]
        after += PHRASE_ESCAPE_SIZE

    transpose = stream[after + PHRASE_COUNT_SIZE] if transposed else 0
    return phrase_id, transpose


def read_tokens(stream: bytes) -> Tuple[ReadToken, ...]:
    """Reads a plane's stream back as the tokens it was written from.

    Args:
        stream: The plane's token stream.

    Returns:
        Tuple[ReadToken, ...]: The tokens in the order they are read.
    """
    tokens: List[ReadToken] = []
    position = 0
    tick = 0
    while position < len(stream):
        span = token_span(stream, position)
        tag = TokenTag(stream[position] & TOKEN_TAG_MASK)
        operand = stream[position] & TOKEN_OPERAND_MASK
        payload = b""
        phrase_id: Optional[int] = None
        transpose = 0
        match tag:
            case TokenTag.LITERAL:
                payload = stream[position + OPCODE_SIZE : position + span.size]
            case TokenTag.PHRASE | TokenTag.TRANSPOSED_PHRASE:
                phrase_id, transpose = _phrase_operands(
                    stream,
                    position,
                    operand,
                    transposed=tag is TokenTag.TRANSPOSED_PHRASE,
                )
            case TokenTag.HOLD:
                pass

        tokens.append(
            ReadToken(
                tag=tag,
                tick=tick,
                size=span.size,
                ticks=span.ticks,
                payload=payload,
                phrase_id=phrase_id,
                transpose=transpose,
            )
        )
        position += span.size
        tick += span.ticks

    return tuple(tokens)
