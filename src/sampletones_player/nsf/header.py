from typing import Final

from sampletones_core.formats.binary import BinaryWriter
from sampletones_player.clock.schedule import PlaySchedule
from sampletones_player.driver.addresses import DriverAddresses
from sampletones_player.information import ProgramInformation, ProgramText, TextLine
from sampletones_player.specification.clock import MICROSECONDS_PER_SECOND
from sampletones_player.specification.nsf import (
    FIRST_SONG,
    NO_BANKSWITCHING,
    NO_EXPANSION_CHIPS,
    NO_NSF2_FEATURES,
    NSF2_LENGTH_UNSTATED,
    NSF_MAGIC,
    NSF_VERSION,
    NTSC_REGION,
    PAL_PLAY_PERIOD_MICROSECONDS,
    SONG_COUNT,
    STRING_ENCODING,
    STRING_FIELD_SIZE,
    STRING_TEXT_SIZE,
)

HEADER_LINE: Final[TextLine] = TextLine(encoding=STRING_ENCODING, room=STRING_TEXT_SIZE, folded=False)
HEADER_TEXT: Final[ProgramText] = ProgramText(title=HEADER_LINE, artist=HEADER_LINE, copyright=HEADER_LINE)


def _write_identity(writer: BinaryWriter) -> None:
    writer.write_bytes(NSF_MAGIC)
    writer.write_uint8(NSF_VERSION)
    writer.write_uint8(SONG_COUNT)
    writer.write_uint8(FIRST_SONG)


def _write_routines(writer: BinaryWriter, addresses: DriverAddresses) -> None:
    writer.write_uint16(addresses.load)
    writer.write_uint16(addresses.init)
    writer.write_uint16(addresses.play)


def _write_strings(writer: BinaryWriter, information: ProgramInformation) -> None:
    fitted = information.fitted(HEADER_TEXT)
    writer.write_fixed_string(fitted.title, STRING_FIELD_SIZE)
    writer.write_fixed_string(fitted.artist, STRING_FIELD_SIZE)
    writer.write_fixed_string(fitted.copyright, STRING_FIELD_SIZE)


def play_period_microseconds(schedule: PlaySchedule) -> int:
    """The NTSC play period the header asks for: one call at the rate ``schedule`` is measured against."""
    return round(MICROSECONDS_PER_SECOND / schedule.play_rate)


def _write_playback(writer: BinaryWriter, schedule: PlaySchedule) -> None:
    writer.write_uint16(play_period_microseconds(schedule))
    writer.write_bytes(NO_BANKSWITCHING)
    writer.write_uint16(PAL_PLAY_PERIOD_MICROSECONDS)
    writer.write_uint8(NTSC_REGION)
    writer.write_uint8(NO_EXPANSION_CHIPS)
    writer.write_uint8(NO_NSF2_FEATURES)
    writer.write_bytes(NSF2_LENGTH_UNSTATED)


def header_to_bytes(
    information: ProgramInformation,
    addresses: DriverAddresses,
    schedule: PlaySchedule,
) -> bytes:
    """Serializes the 128-byte header a console's NSF player reads a file through.

    The header states where the image loads and which routines start and drive it, so the whole
    of what the console needs to run the driver is named here. The song is one tune played on
    the 2A03 alone, loaded whole at a fixed address and driven at the NTSC rate the schedule
    counts in. Each line of text reaches its fixed 32-byte field as the part of itself
    :data:`HEADER_LINE` holds, which leaves the field its terminator.

    Args:
        information: The text the file is listed under.
        addresses: Where the driver loads and which addresses its routines answer at.
        schedule: The schedule the song plays on, whose rate the header asks the player to call at.

    Returns:
        bytes: The header, ready for the image and the song to follow it.
    """
    writer = BinaryWriter()
    _write_identity(writer)
    _write_routines(writer, addresses)
    _write_strings(writer, information)
    _write_playback(writer, schedule)
    return writer.data
