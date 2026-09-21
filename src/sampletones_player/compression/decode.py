from typing import List, Tuple

from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.compression.planes.flags import flagged_ticks
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.compression.planes.symbols import unpack_plane
from sampletones_player.specification.binary import BYTE_VALUES
from sampletones_player.specification.compression import (
    PHRASE_ID_ESCAPE,
    TOKEN_OPERAND_MASK,
    TOKEN_TAG_MASK,
    TokenTag,
)
from sampletones_player.specification.planes import (
    PLANES,
    SINGLE_TICK,
    Plane,
    PlaneRole,
    plane_index,
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


def decode_plane(
    data: bytes,
    table: PhraseTable,
    plane: Plane,
    ticks: int,
) -> bytes:
    """Plays a plane's token stream back into the values it writes, tick by tick.

    This is the reading the driver performs, stated where it is testable: every encoding is held
    against it, so what the console plays and what the encoder meant are the same values. A
    symbol covers the ticks its own count states, so the reading stops once the ticks the song
    lasts are covered, wherever in a symbol that falls. An absent plane's empty stream plays the
    value the driver seeds it to throughout.

    Args:
        data: The plane's token stream.
        table: The dictionary the tokens name.
        plane: The plane the stream belongs to, for the byte it seeds to and how its byte divides.
        ticks: The ticks the song lasts.

    Returns:
        bytes: The values the plane writes, one per tick.
    """
    form = plane.form
    if not data:
        return bytes((plane.seeded,)) * ticks

    symbols = bytearray()
    current = form.symbol(plane.seeded, SINGLE_TICK)
    covered = 0
    position = 0
    while covered < ticks:
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
        symbols.extend(played)
        covered += sum(form.repeated(symbol) for symbol in played)

    return unpack_plane(bytes(symbols), form)[:ticks]


def decode_planes(compressed: CompressedPlanes) -> SongPlanes:
    """Plays a song's token streams back into the planes they were written from.

    A bend plane holds a value per tick its channel flags, so each is played for as many values
    as its channel's value plane flags once that plane is played back.

    Args:
        compressed: The dictionary, the streams and the ticks the song lasts.

    Returns:
        SongPlanes: Every plane, in the order the song block writes them.
    """
    played: List[bytes] = []
    for plane, stream in zip(PLANES, compressed.streams, strict=True):
        reach = (
            flagged_ticks(played[plane_index(plane.channel, PlaneRole.VALUE)])
            if plane.spans_flagged_ticks
            else compressed.ticks
        )
        played.append(decode_plane(stream, compressed.phrases, plane, reach))

    return SongPlanes(planes=PlaneOrder.across(played))
