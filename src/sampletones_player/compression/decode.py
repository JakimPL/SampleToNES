from typing import Tuple

from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.compression.planes.flags import flagged_ticks
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.specification.binary import BYTE_VALUES
from sampletones_player.specification.compression import (
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
    against it, so what the console plays and what the encoder meant are the same values. An
    absent plane's empty stream plays the value every plane starts at throughout.

    Args:
        data: The plane's token stream.
        table: The dictionary the tokens name.
        ticks: The ticks the song lasts.

    Returns:
        bytes: The values the plane writes, one per tick.
    """
    if not data:
        return bytes((INITIAL_PLANE_VALUE,)) * ticks

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


def _tone_planes(
    compressed: CompressedPlanes,
    control: bytes,
    value: bytes,
    bend: bytes,
) -> Tuple[bytes, bytes, bytes]:
    """A tone channel's planes played back, its bend plane as long as its value plane flags."""
    played = decode_plane(value, compressed.phrases, compressed.ticks)
    return (
        decode_plane(control, compressed.phrases, compressed.ticks),
        played,
        decode_plane(bend, compressed.phrases, flagged_ticks(played)),
    )


def decode_planes(compressed: CompressedPlanes) -> SongPlanes:
    """Plays a song's token streams back into the planes they were written from.

    A bend plane holds a value per tick its channel flags, so each is played for as many values
    as its channel's value plane flags once that plane is played back.

    Args:
        compressed: The dictionary, the streams and the ticks the song lasts.

    Returns:
        SongPlanes: The planes under the channel each belongs to.
    """
    streams = compressed.streams
    played = PlaneOrder.across(
        (
            *_tone_planes(compressed, streams.pulse1_control, streams.pulse1_value, streams.pulse1_bend),
            *_tone_planes(compressed, streams.pulse2_control, streams.pulse2_value, streams.pulse2_bend),
            *_tone_planes(compressed, streams.triangle_control, streams.triangle_value, streams.triangle_bend),
            decode_plane(streams.noise_control, compressed.phrases, compressed.ticks),
            decode_plane(streams.noise_value, compressed.phrases, compressed.ticks),
        )
    )
    return SongPlanes.from_order(played)
