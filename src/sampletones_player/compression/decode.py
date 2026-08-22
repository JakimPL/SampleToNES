from typing import Tuple

from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.specification.compression import (
    BYTE_VALUES,
    INITIAL_PLANE_VALUE,
    PHRASE_ID_ESCAPE,
    TOKEN_OPERAND_MASK,
    TOKEN_TAG_MASK,
    TokenTag,
)


def _phrase_values(
    operand: int,
    data: bytes,
    position: int,
    table: PhraseTable,
    *,
    transposed: bool,
) -> Tuple[bytes, int]:
    phrase_id = operand
    if operand == PHRASE_ID_ESCAPE:
        phrase_id = data[position]
        position += 1

    ticks = data[position] + 1
    position += 1
    transpose = 0
    if transposed:
        transpose = data[position]
        position += 1

    body = table[phrase_id].body
    last = len(body) - 1
    played = bytes((body[min(offset, last)] + transpose) % BYTE_VALUES for offset in range(ticks))
    return played, position


def decode_plane(data: bytes, table: PhraseTable, ticks: int) -> bytes:
    """Plays a plane's token stream back into the values it writes, tick by tick.

    This is the reading the driver performs, stated where it is testable: every encoding is held
    against it, so what the console plays and what the encoder meant are the same values.

    Args:
        data: The plane's token stream.
        table: The dictionary the tokens name.
        ticks: The ticks the song lasts.

    Returns:
        bytes: The values the plane writes, one per tick.
    """
    values = bytearray()
    current = INITIAL_PLANE_VALUE
    position = 0
    while len(values) < ticks:
        opcode = data[position]
        position += 1
        operand = opcode & TOKEN_OPERAND_MASK
        match TokenTag(opcode & TOKEN_TAG_MASK):
            case TokenTag.HOLD:
                played = bytes([current]) * (operand + 1)
            case TokenTag.LITERAL:
                played = data[position : position + operand + 1]
                position += operand + 1
            case TokenTag.PHRASE:
                played, position = _phrase_values(
                    operand,
                    data,
                    position,
                    table,
                    transposed=False,
                )
            case TokenTag.TRANSPOSED_PHRASE:
                played, position = _phrase_values(
                    operand,
                    data,
                    position,
                    table,
                    transposed=True,
                )

        current = played[-1]
        values.extend(played)

    return bytes(values[:ticks])


def decode_planes(compressed: CompressedPlanes) -> SongPlanes:
    """Plays a song's eight token streams back into the planes they were written from.

    Args:
        compressed: The dictionary, the streams and the ticks the song lasts.

    Returns:
        SongPlanes: The eight planes, two per channel.
    """
    played = PlaneOrder.across(
        decode_plane(
            stream,
            compressed.phrases,
            compressed.ticks,
        )
        for stream in compressed.streams
    )
    return SongPlanes.from_order(played)
