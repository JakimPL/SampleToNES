from sampletones_player.block.song import song_to_bytes
from sampletones_player.driver.image import DriverImage
from sampletones_player.information import ProgramInformation
from sampletones_player.nsf.header import header_to_bytes
from sampletones_player.song import Song
from sampletones_player.specification.memory import PROGRAM_SIZE
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import save_binary


def song_room(image: DriverImage) -> int:
    """The bytes an NSF leaves its song: the program area behind the driver.

    Args:
        image: The assembled driver the file carries.

    Returns:
        int: The space the song block has to fit in.
    """
    return PROGRAM_SIZE - len(image.code)


def nsf_to_bytes(
    song: Song,
    information: ProgramInformation,
    image: DriverImage,
) -> bytes:
    """Builds the bytes of a playable NSF: the header, the driver and the song it plays.

    The three parts sit in the order the console loads them, the song following the driver at
    the address the image reports, so the space the song has to fit in is what the program area
    leaves behind the code.

    Args:
        song: The streams, the clock and the loop point to play.
        information: The text the file is listed under.
        image: The assembled driver the file carries, and the addresses its routines answer at.

    Returns:
        bytes: The whole file.

    Raises:
        SongTooLargeError: If the song takes more room than the driver leaves it.
    """
    data = song_to_bytes(song, song_room(image))

    return header_to_bytes(information, image.addresses, song.schedule) + image.code + data


def write_nsf(
    filepath: Pathlike,
    song: Song,
    information: ProgramInformation,
    image: DriverImage,
) -> None:
    """Exports a song to a playable ``.nsf`` file.

    Args:
        filepath: The file to write.
        song: The streams, the clock and the loop point to play.
        information: The text the file is listed under.
        image: The assembled driver the file carries, and the addresses its routines answer at.

    Raises:
        SongTooLargeError: If the song takes more room than the driver leaves it.
        OSError: If the destination cannot be written.
    """
    save_binary(filepath, nsf_to_bytes(song, information, image))
