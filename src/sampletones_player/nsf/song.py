from typing import Sequence, Tuple

from sampletones_core.formats.binary import BinaryWriter
from sampletones_player.registers.base import ChannelRegisters
from sampletones_player.song import Song
from sampletones_player.specification.channels import CHANNEL_ORDER
from sampletones_player.specification.song import (
    MAX_STREAM_OFFSET,
    NO_LOOP,
    SONG_HEADER_SIZE,
)
from sampletones_shared.exceptions import SongTooLargeError


def _stream_to_bytes(stream: Sequence[ChannelRegisters]) -> bytes:
    writer = BinaryWriter()
    for registers in stream:
        for value in registers.values:
            writer.write_uint8(value)

    return writer.data


def _stream_offsets(bodies: Sequence[bytes]) -> Tuple[int, ...]:
    offsets = []
    offset = SONG_HEADER_SIZE
    for body in bodies:
        offsets.append(offset)
        offset += len(body)

    return tuple(offsets)


def _write_header(
    writer: BinaryWriter,
    song: Song,
    offsets: Sequence[int],
) -> None:
    step = song.schedule.fixed_point_step
    writer.write_uint8(step.whole)
    writer.write_uint16(step.fraction)
    writer.write_uint16(song.ticks)
    writer.write_uint16(NO_LOOP if song.loop_tick is None else song.loop_tick)
    for offset in offsets:
        writer.write_uint16(offset)


def _validate_space(size: int, available_bytes: int) -> None:
    if size > available_bytes:
        raise SongTooLargeError(f"the song takes {size} bytes and {available_bytes} are free")


def _validate_offsets(offsets: Sequence[int]) -> None:
    for channel, offset in zip(CHANNEL_ORDER, offsets):
        if offset > MAX_STREAM_OFFSET:
            raise SongTooLargeError(
                f"the {channel.value} stream starts {offset} bytes into the song "
                f"and its header states at most {MAX_STREAM_OFFSET}",
            )


def song_to_bytes(song: Song, available_bytes: int) -> bytes:
    """Serializes a song to the bytes the driver reads it from.

    The header states the clock and the length, then names where each channel's stream begins as
    a distance from the song's own first byte, so the whole block plays from wherever the file
    loads it and each channel can later be compressed on its own.

    Args:
        song: The streams, the clock and the loop point to write.
        available_bytes: The space the song has to fit in.

    Returns:
        bytes: The song header followed by the four channel streams.

    Raises:
        SongTooLargeError: If the song takes more than ``available_bytes``, or reaches further
            into itself than a stream offset states.
    """
    bodies = tuple(_stream_to_bytes(stream) for stream in song.streams.padded)
    offsets = _stream_offsets(bodies)
    _validate_space(SONG_HEADER_SIZE + sum(len(body) for body in bodies), available_bytes)
    _validate_offsets(offsets)

    writer = BinaryWriter()
    _write_header(writer, song, offsets)
    for body in bodies:
        writer.write_bytes(body)

    return writer.data
