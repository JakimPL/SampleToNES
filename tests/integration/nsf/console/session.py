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

    Raises:
        ValueError: If the song repeats, which leaves it no last tick to reach past. A run over
            one covers the calls :func:`play_calls_reaching` measures.
    """
    if song.loop_tick is not None:
        raise ValueError(f"a song repeating from tick {song.loop_tick} runs for as long as it is called")

    calls = 0
    while song.tick_at(calls) is not None:
        calls += 1

    return calls + TRAILING_CALLS


def play_calls_reaching(song: Song, ticks: int) -> int:
    """How many play calls carry a song's streams past ``ticks`` of its own time.

    A song that repeats runs on for as long as it is called, so a run over one is measured by the
    ticks it is to cover rather than by where the streams end.

    Args:
        song: The song the driver plays.
        ticks: The ticks the run is to reach past.

    Returns:
        int: The number of play calls the run covers.
    """
    calls = 0
    while song.schedule.ticks_at(calls) <= ticks:
        calls += 1

    return calls


def captured_file_trace(data: bytes, song: Song) -> RegisterTrace:
    """Runs an exported file on a 6502 and answers with every APU write it made.

    Args:
        data: The whole ``.nsf`` file, header included.
        song: The song the file plays, which states how far the run reaches.

    Returns:
        RegisterTrace: The writes of the initialization and of every play call in the run.
    """
    return captured_run(data, play_calls_covering(song))


def captured_run(data: bytes, play_calls: int) -> RegisterTrace:
    """Runs an exported file for a stated number of calls and answers with every APU write.

    Args:
        data: The whole ``.nsf`` file, header included.
        play_calls: How many play calls the run covers.

    Returns:
        RegisterTrace: The writes of the initialization and of every play call in the run.
    """
    image = DriverImage.load()
    console = Console(data, image.addresses)
    return console.trace(play_calls)


def captured_trace(song: Song, information: NSFInformation) -> RegisterTrace:
    """Exports a song, runs the file on a 6502 and answers with every APU write it made.

    Args:
        song: The song to export and play, which states how far the run reaches.
        information: The text the exported header carries.

    Returns:
        RegisterTrace: The writes of the initialization and of every play call in the run.
    """
    return captured_file_trace(nsf_to_bytes(song, information, DriverImage.load()), song)


def captured_trace_over(
    song: Song,
    information: NSFInformation,
    play_calls: int,
) -> RegisterTrace:
    """Exports a song and runs the file for ``play_calls`` calls, a repeating song included.

    Args:
        song: The song to export and play.
        information: The text the exported header carries.
        play_calls: How many play calls the run covers.

    Returns:
        RegisterTrace: The writes of the initialization and of every play call in the run.
    """
    return captured_run(nsf_to_bytes(song, information, DriverImage.load()), play_calls)
