from sampletones_core.formats.binary import BinaryWriter
from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.nsf.layout import SongLayout
from sampletones_player.song import Song
from sampletones_player.specification.song import MAX_BLOCK_OFFSET, NO_LOOP
from sampletones_shared.exceptions import SongTooLargeError


def _write_header(
    writer: BinaryWriter,
    song: Song,
    layout: SongLayout,
) -> None:
    step = song.schedule.fixed_point_step
    writer.write_uint8(step.whole)
    writer.write_uint16(step.fraction)
    writer.write_uint16(song.ticks)
    writer.write_uint16(NO_LOOP if song.loop_tick is None else song.loop_tick)
    writer.write_uint16(layout.timer_table)
    writer.write_uint16(layout.phrase_table)
    for offset in layout.streams:
        writer.write_uint16(offset)

    for offset in layout.loop_entries:
        writer.write_uint16(offset)


def _write_timer_table(writer: BinaryWriter, pitches: PitchTable) -> None:
    writer.write_bytes(pitches.data)


def _write_phrase_table(
    writer: BinaryWriter,
    phrases: PhraseTable,
    layout: SongLayout,
) -> None:
    writer.write_uint8(len(phrases))
    for offset in layout.bodies:
        writer.write_uint16(offset)

    for phrase in phrases.phrases:
        writer.write_uint8(phrase.length)
        writer.write_bytes(phrase.body)


def _write_streams(writer: BinaryWriter, streams: PlaneOrder) -> None:
    for stream in streams:
        writer.write_bytes(stream)


def _validate_space(size: int, available_bytes: int) -> None:
    if size > available_bytes:
        raise SongTooLargeError(f"the song takes {size} bytes and {available_bytes} are free")


def _validate_offsets(layout: SongLayout) -> None:
    for part, offset in layout.stated:
        if offset > MAX_BLOCK_OFFSET:
            raise SongTooLargeError(
                f"the {part} lies {offset} bytes into the song " f"and its header states at most {MAX_BLOCK_OFFSET}",
            )


def song_to_bytes(song: Song, available_bytes: int) -> bytes:
    """Serializes a song to the bytes the driver reads it from.

    The header states the clock, the length and where each of the song's parts begins, so the
    whole block plays from wherever the file loads it: the timer every pitch sounds at, the
    dictionary the tokens name, and the eight token streams the channels decode a tick at a
    time. A song that repeats also states the byte each stream is re-entered at, which is the
    whole of what a loop restores.

    Args:
        song: The compressed planes, the timer table, the clock and the loop point to write.
        available_bytes: The space the song has to fit in.

    Returns:
        bytes: The song header, the timer table, the dictionary and the eight token streams.

    Raises:
        SongTooLargeError: If the song takes more than ``available_bytes``, or reaches further
            into itself than an offset it states.
        ValueError: If a stream spans the song's loop tick rather than starting a token there.
    """
    layout = SongLayout.of(song)
    _validate_space(layout.size, available_bytes)
    _validate_offsets(layout)

    writer = BinaryWriter()
    _write_header(writer, song, layout)
    _write_timer_table(writer, song.pitches)
    _write_phrase_table(writer, song.planes.phrases, layout)
    _write_streams(writer, song.planes.streams)
    return writer.data
