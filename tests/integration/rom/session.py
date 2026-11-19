from typing import AbstractSet, Final, FrozenSet, List

from sampletones_core.project.voices.sample import Sample
from sampletones_player.builder import song_from_reconstruction
from sampletones_player.compression.scheme import CompressionScheme
from sampletones_player.driver.image import DriverImage
from sampletones_player.information import ProgramInformation
from sampletones_player.rom.file import rom_to_bytes
from sampletones_player.shell.image import ShellImage
from sampletones_player.shell.patterns import load_patterns
from sampletones_player.song import Song
from sampletones_player.specification.memory import RAM_SIZE
from sampletones_tools.console.rom.controller import NO_BUTTONS, Button
from sampletones_tools.console.rom.frame import Frame
from sampletones_tools.console.rom.machine import ROMConsole
from sampletones_tools.console.rom.screen import Screen
from sampletones_tools.player.graphics.picture.picture import Picture
from sampletones_tools.player.trace.trace import RegisterTrace
from tests.integration.nsf.console.session import play_calls_covering, play_calls_reaching

CLEARED_MEMORY: Final[bytes] = bytes(RAM_SIZE)
NOTHING_WATCHED: Final[FrozenSet[int]] = frozenset()
SETTLING_FRAMES: Final[int] = 3
FIRST_PLAYED_FRAME: Final[int] = 1
ROUNDS: Final[int] = 2


def reclocked_song(sample: Sample, nes_frequency: int, *, looping: bool) -> Song:
    """The sample built at ``nes_frequency``, repeating from the middle of its ticks where it loops."""
    reclocked = sample.reconstruction.with_nes_frequency(nes_frequency)
    song = song_from_reconstruction(reclocked, loop_tick=None, scheme=CompressionScheme.SEARCH)
    if not looping:
        return song

    return song_from_reconstruction(reclocked, loop_tick=song.ticks // 2, scheme=CompressionScheme.SEARCH)


def calls_through(song: Song) -> int:
    """The frames a run takes past a song's end, or round its loop ``ROUNDS`` times."""
    if song.loop_tick is None:
        return play_calls_covering(song)

    return play_calls_reaching(song, song.ticks + ROUNDS * (song.ticks - song.loop_tick))


def cartridge(song: Song, information: ProgramInformation) -> bytes:
    """The cartridge image a song is exported as, with the shipped driver, shell and tiles."""
    return rom_to_bytes(song, information, DriverImage.load(), ShellImage.load(), load_patterns())


def booted(
    data: bytes,
    *,
    memory: bytes = CLEARED_MEMORY,
    watched: AbstractSet[int] = NOTHING_WATCHED,
) -> ROMConsole:
    """A console that has run a cartridge from power-on to its first frame interrupt."""
    console = ROMConsole(data, memory=memory, watched=watched)
    console.boot()
    return console


def cartridge_trace(
    song: Song,
    information: ProgramInformation,
    play_calls: int,
    *,
    memory: bytes = CLEARED_MEMORY,
) -> RegisterTrace:
    """Exports a song as a cartridge and answers with every APU write of its boot and ``play_calls`` frames."""
    return ROMConsole(cartridge(song, information), memory=memory).trace(play_calls)


def run_frames(console: ROMConsole, frames: int, buttons: Button = NO_BUTTONS) -> List[Frame]:
    """Runs ``frames`` frames with ``buttons`` held through each of them."""
    return [console.frame(buttons) for _ in range(frames)]


def paused_after(console: ROMConsole, played: int) -> List[Frame]:
    """Plays ``played`` frames, presses START on the last, and lets the screen settle.

    The shell plays a frame before it reads the controller, so the frame START is held through
    still plays, and the song stops with ``played`` frames behind it. The shell then composes two
    channels a frame, and once every reading has been written the screen holds still.

    Returns:
        List[Frame]: Every frame of the run, the press and the settling included.

    Raises:
        ValueError: If ``played`` is below 1, since the press itself falls on a played frame.
    """
    if played < FIRST_PLAYED_FRAME:
        raise ValueError(f"played must be at least {FIRST_PLAYED_FRAME}, got {played}")

    frames = run_frames(console, played - 1)
    frames.append(console.frame(Button.START))
    frames.extend(run_frames(console, SETTLING_FRAMES))
    return frames


def shown(screen: Screen) -> Picture:
    """The parts of what the picture processor holds that a picture states."""
    return Picture(
        nametable=screen.nametable,
        attributes=screen.attributes,
        palette=screen.palette,
        sprites=screen.sprites,
    )


def paused_screen(song: Song, information: ProgramInformation, played: int) -> Picture:
    """What a cartridge of the song shows once paused after ``played`` frames and left to settle."""
    console = booted(cartridge(song, information))
    paused_after(console, played)
    return shown(console.screen)
