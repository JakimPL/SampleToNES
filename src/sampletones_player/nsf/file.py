from sampletones_player.driver.image import DriverImage
from sampletones_player.nsf.header import header_to_bytes
from sampletones_player.nsf.information import NSFInformation
from sampletones_player.nsf.song import song_to_bytes
from sampletones_player.song import Song
from sampletones_player.specification.nsf import PROGRAM_SIZE
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import save_binary


def nsf_to_bytes(song: Song, information: NSFInformation) -> bytes:
    """Builds the bytes of a playable NSF: the header, the driver and the song it plays.

    The three parts sit in the order the console loads them, the song following the driver at
    the address the image reports, so the space the song has to fit in is what the program area
    leaves behind the code.

    Args:
        song: The streams, the clock and the loop point to play.
        information: The text fields the file is listed under.

    Returns:
        bytes: The whole file.

    Raises:
        SongTooLargeError: If the song takes more room than the driver leaves it.
        ValueError: If the committed driver lays out something other than the addresses it is
            built to answer at.
    """
    image = DriverImage.load()
    data = song_to_bytes(song, PROGRAM_SIZE - len(image.code))

    return header_to_bytes(information, image.addresses) + image.code + data


def write_nsf(filepath: Pathlike, song: Song, information: NSFInformation) -> None:
    """Exports a song to a playable ``.nsf`` file.

    Args:
        filepath: The file to write.
        song: The streams, the clock and the loop point to play.
        information: The text fields the file is listed under.

    Raises:
        SongTooLargeError: If the song takes more room than the driver leaves it.
        OSError: If the destination cannot be written.
    """
    save_binary(filepath, nsf_to_bytes(song, information))
