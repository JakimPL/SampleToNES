from typing import Final

from sampletones_player.driver.image import DriverImage
from sampletones_player.nsf.file import nsf_to_bytes
from sampletones_player.nsf.information import NSFInformation
from sampletones_player.song import Song
from sampletones_player.trace.trace import RegisterTrace
from tests.integration.nsf.console.machine import Console

TRAILING_CALLS: Final[int] = 2


def play_calls_covering(song: Song) -> int:
    """How many play calls carry a song from its first tick past its last.

    A stream built below the hardware rate holds its tick through some calls, so the count follows
    the song's own schedule rather than its tick count. The run reaches a few calls beyond the end
    as well, which is where a song without a loop is seen to stop.

    Args:
        song: The song the driver plays.

    Returns:
        int: The number of play calls the run covers.
    """
    calls = 0
    while song.tick_at(calls) is not None:
        calls += 1

    return calls + TRAILING_CALLS


def captured_trace(song: Song, information: NSFInformation) -> RegisterTrace:
    """Exports a song, runs the file on a 6502 and answers with every APU write it made.

    Args:
        song: The song to export and play.
        information: The text the exported header carries.

    Returns:
        RegisterTrace: The writes of the initialisation and of every play call in the run.
    """
    image = DriverImage.load()
    console = Console(nsf_to_bytes(song, information), image.addresses)
    return console.trace(play_calls_covering(song))
