from sampletones_core.formats.binary import BinaryWriter
from sampletones_player.driver.addresses import DriverAddresses
from sampletones_player.nsf.information import NSFInformation
from sampletones_player.specification.clock import PLAY_PERIOD_MICROSECONDS
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
    STRING_FIELD_SIZE,
)


def _write_identity(writer: BinaryWriter) -> None:
    writer.write_bytes(NSF_MAGIC)
    writer.write_uint8(NSF_VERSION)
    writer.write_uint8(SONG_COUNT)
    writer.write_uint8(FIRST_SONG)


def _write_routines(writer: BinaryWriter, addresses: DriverAddresses) -> None:
    writer.write_uint16(addresses.load)
    writer.write_uint16(addresses.init)
    writer.write_uint16(addresses.play)


def _write_strings(writer: BinaryWriter, information: NSFInformation) -> None:
    writer.write_fixed_string(information.title, STRING_FIELD_SIZE)
    writer.write_fixed_string(information.artist, STRING_FIELD_SIZE)
    writer.write_fixed_string(information.copyright, STRING_FIELD_SIZE)


def _write_playback(writer: BinaryWriter) -> None:
    writer.write_uint16(PLAY_PERIOD_MICROSECONDS)
    writer.write_bytes(NO_BANKSWITCHING)
    writer.write_uint16(PAL_PLAY_PERIOD_MICROSECONDS)
    writer.write_uint8(NTSC_REGION)
    writer.write_uint8(NO_EXPANSION_CHIPS)
    writer.write_uint8(NO_NSF2_FEATURES)
    writer.write_bytes(NSF2_LENGTH_UNSTATED)


def header_to_bytes(
    information: NSFInformation,
    addresses: DriverAddresses,
) -> bytes:
    """Serializes the 128-byte header a console's NSF player reads a file through.

    The header states where the image loads and which routines start and drive it, so the whole
    of what the console needs to run the driver is named here. The song is one tune played on
    the 2A03 alone, loaded whole at a fixed address and driven at the NTSC rate the schedule
    counts in.

    Args:
        information: The text fields the file is listed under.
        addresses: Where the driver loads and which addresses its routines answer at.

    Returns:
        bytes: The header, ready for the image and the song to follow it.
    """
    writer = BinaryWriter()
    _write_identity(writer)
    _write_routines(writer, addresses)
    _write_strings(writer, information)
    _write_playback(writer)
    return writer.data
