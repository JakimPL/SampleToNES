from typing import Sequence

from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.specification.binary import BYTE_VALUES
from sampletones_player.specification.compression import INITIAL_PLANE_VALUE
from sampletones_tools.codec.study.sandbox.tokens import Hold, Literal, Play, SetHold, StudyToken, WideHold


def _played(
    token: Play,
    table: PhraseTable,
) -> bytes:
    body = table[token.phrase_id].body
    last = len(body) - 1
    return bytes((body[min(offset, last)] + token.transpose) % BYTE_VALUES for offset in range(token.ticks))


def play_tokens(
    tokens: Sequence[StudyToken],
    table: PhraseTable,
    ticks: int,
) -> bytes:
    """Plays a plane's tokens back into the values they write, tick by tick.

    This is the reading a driver of the grammar would perform, stated over tokens: a hold
    keeps the value reached, a phrase played past its end holds its final value onward, and
    every plane opens on the value the driver seeds it to.

    Args:
        tokens: The tokens the plane is written as, in the order they are read.
        table: The dictionary the tokens name.
        ticks: The ticks the song lasts.

    Returns:
        bytes: The values the plane writes, one per tick.
    """
    values = bytearray()
    current = INITIAL_PLANE_VALUE
    for token in tokens:
        match token:
            case Hold() | WideHold():
                played = bytes([current]) * token.ticks
            case SetHold():
                played = bytes([token.value]) * token.ticks
            case Literal():
                played = token.values
            case Play():
                played = _played(token, table)

        current = played[-1]
        values.extend(played)

    return bytes(values[:ticks])
