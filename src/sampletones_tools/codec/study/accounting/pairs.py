from typing import Final, Sequence

from sampletones_player.specification.compression import TokenTag
from sampletones_tools.codec.study.accounting.finding import NOTHING, Finding
from sampletones_tools.codec.study.accounting.runs import ramps
from sampletones_tools.codec.study.accounting.tokens import ReadToken

SET_HOLD_SIZE: Final[int] = 2
SINGLE_VALUE: Final[int] = 1
RAMP_TOKEN_SIZE: Final[int] = 3
MIN_RAMP_LENGTH: Final[int] = 3


def set_holds(tokens: Sequence[ReadToken]) -> Finding:
    """What a set-then-hold token would spare on a single value followed by a hold (H3).

    A plane that steps to a value and rests there pays a literal of one value and a hold, three
    bytes. A token carrying the value and the count together takes two bytes on an opcode of its
    own, which is the bound stated here; on the free escape it takes three and spares nothing.

    Args:
        tokens: The tokens of one plane's stream.

    Returns:
        Finding: The bytes such pairs take, and the bytes a two-byte token would spare.
    """
    finding = NOTHING
    for token, following in zip(tokens, tokens[1:]):
        if token.tag is TokenTag.LITERAL and len(token.payload) == SINGLE_VALUE and following.tag is TokenTag.HOLD:
            now = token.size + following.size
            finding += Finding(now, now - SET_HOLD_SIZE)

    return finding


def ramps_in_literals(tokens: Sequence[ReadToken]) -> Finding:
    """What a ramp token would spare on constant-step runs inside literals (H6).

    A fade or a slide spells every step out. A token naming the first value, the step and the
    count takes three bytes however long the ramp runs.

    Args:
        tokens: The tokens of one plane's stream.

    Returns:
        Finding: The payload bytes lying in ramps, and the bytes ramp tokens would spare.
    """
    finding = NOTHING
    for token in tokens:
        if token.tag is not TokenTag.LITERAL:
            continue

        for length in ramps(token.payload):
            if length >= MIN_RAMP_LENGTH:
                finding += Finding(length, max(0, length - RAMP_TOKEN_SIZE))

    return finding
