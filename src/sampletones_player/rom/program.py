from typing import Final

from sampletones_core.formats.binary import BinaryWriter
from sampletones_player.information import ProgramInformation, ProgramText, TextLine
from sampletones_player.rom.clock import ProgramClock
from sampletones_player.specification.program import (
    ARTIST_COLUMNS,
    COPYRIGHT_COLUMNS,
    FRAME_COUNT_SIZE,
    PROGRESS_SIZE,
    TITLE_COLUMNS,
)
from sampletones_player.specification.screen import FIRST_GLYPH, LAST_GLYPH

SCREEN_ENCODING: Final[str] = "ascii"
BLANK_CELL: Final[str] = " "
UNKNOWN_CELL: Final[str] = "?"
BYTE_ORDER: Final = "little"
SCREEN_TEXT: Final[ProgramText] = ProgramText(
    title=TextLine(encoding=SCREEN_ENCODING, room=TITLE_COLUMNS, folded=True),
    artist=TextLine(encoding=SCREEN_ENCODING, room=ARTIST_COLUMNS, folded=True),
    copyright=TextLine(encoding=SCREEN_ENCODING, room=COPYRIGHT_COLUMNS, folded=True),
)


def screen_line(text: str, columns: int) -> bytes:
    """A line of text as the tiles of its field, padded with blank cells to the field's width.

    The screen's font sits at the character codes of printable ASCII, so a character's code is
    the tile that draws it, and a character the font leaves out is shown as a question mark.

    Raises:
        ValueError: If the text holds more characters than the field.
    """
    if len(text) > columns:
        raise ValueError(f"the field holds {columns} characters, got {len(text)}")

    drawn = "".join(character if FIRST_GLYPH <= ord(character) <= LAST_GLYPH else UNKNOWN_CELL for character in text)
    return drawn.ljust(columns, BLANK_CELL).encode(SCREEN_ENCODING)


def program_block(song_address: int, information: ProgramInformation, clock: ProgramClock) -> bytes:
    """Lays out what the cartridge's screen shows about a song, in the order the shell reads it.

    Args:
        song_address: Where the song block lies, which the shell states it was built for.
        information: The text the program is listed under, each line fitted to its field here.
        clock: The frames the song's time and progress are counted in.

    Returns:
        bytes: The program block.
    """
    shown = information.fitted(SCREEN_TEXT)
    writer = BinaryWriter()
    writer.write_uint16(song_address)
    for text, columns in (
        (shown.title, TITLE_COLUMNS),
        (shown.artist, ARTIST_COLUMNS),
        (shown.copyright, COPYRIGHT_COLUMNS),
    ):
        writer.write_bytes(screen_line(text, columns))

    writer.write_bytes(bytes(clock.total_time))
    writer.write_bytes(clock.total_frames.to_bytes(FRAME_COUNT_SIZE, BYTE_ORDER))
    writer.write_bytes(clock.progress_step.to_bytes(PROGRESS_SIZE, BYTE_ORDER))
    writer.write_bytes(clock.loop_frames.to_bytes(FRAME_COUNT_SIZE, BYTE_ORDER))
    writer.write_bytes(bytes(clock.loop_time))
    writer.write_uint16(clock.loop_second)
    writer.write_bytes(clock.loop_progress.to_bytes(PROGRESS_SIZE, BYTE_ORDER))
    return writer.data
