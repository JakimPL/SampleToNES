from dataclasses import dataclass
from typing import AbstractSet, Final, List, Optional, Tuple

import pytest

from sampletones_player.driver.image import DriverImage
from sampletones_player.information import ProgramInformation
from sampletones_player.shell.image import ShellImage
from sampletones_player.song import Song
from sampletones_tools.console.rom.controller import Button
from sampletones_tools.console.rom.frame import Frame
from sampletones_tools.console.rom.machine import ROMConsole
from sampletones_tools.console.rom.registers import SPRITE_TRANSFER, VideoRegister
from sampletones_tools.console.rom.timing import (
    FRAME_CYCLES,
    SPRITE_TRANSFER_ALIGNMENT_CYCLES,
    VERTICAL_BLANK_CYCLES,
)
from sampletones_tools.console.rom.write import VideoWrite
from tests.integration.rom.session import CLEARED_MEMORY, NOTHING_WATCHED, booted, calls_through, cartridge, run_frames
from tests.integration.rom.songs import DECK_SONG_TICKS, deck_song
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

NTSC_RATE: Final[int] = 60
HALF_RATE: Final[int] = 30
FAST_RATE: Final[int] = 300
LOOP_TICK: Final[int] = DECK_SONG_TICKS // 2
NMI_VECTOR_INDEX: Final[int] = 0
SWITCHED_OFF: Final[int] = 0x00
PAUSED_FRAMES: Final[int] = 4
INFORMATION: Final[ProgramInformation] = ProgramInformation(title="Frames", artist="Budget")
CELL_REGISTERS: Final[Tuple[int, ...]] = (
    VideoRegister.ADDRESS.address,
    VideoRegister.DATA.address,
    SPRITE_TRANSFER,
)


@dataclass(frozen=True)
class FrameRun:
    """What a cartridge did from power-on through every frame of a song.

    Attributes:
        boot: The stretches between the vertical blanks of the boot.
        frames: Every frame after it.
    """

    boot: Tuple[Frame, ...]
    frames: List[Frame]

    @property
    def stores(self) -> List[VideoWrite]:
        """Every store the frames after the boot made to the picture processor."""
        return [write for frame in self.frames for write in frame.video]

    @property
    def boot_stores(self) -> List[VideoWrite]:
        """Every store the boot made to the picture processor."""
        return [write for frame in self.boot for write in frame.video]


def frame_run(song: Song, *, watched: AbstractSet[int] = NOTHING_WATCHED) -> FrameRun:
    """Boots a cartridge of the song and runs it past the song's end, or round its loop."""
    console = ROMConsole(cartridge(song, INFORMATION), memory=CLEARED_MEMORY, watched=watched)
    boot = console.boot()
    return FrameRun(boot=boot, frames=run_frames(console, calls_through(song)))


class TestEveryFrameKeepsItsBudget(BaseTestSuite):
    """Once the picture is drawn, its cells can be written only inside the vertical blank.

    The interrupt sends the sprites and the composed cells first and plays the song afterwards,
    so however much a song plays in a frame, the stores to the picture processor land early in
    it. The scroll and the control follow the cells, since writing an address moves the scroll
    the picture is drawn from. Whatever the frame does after them ends before the next frame.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        nes_frequency: int
        loop_tick: Optional[int]

    test_cases = (
        TestCase(label="60-hz", nes_frequency=NTSC_RATE, loop_tick=None),
        TestCase(label="30-hz", nes_frequency=HALF_RATE, loop_tick=None),
        TestCase(label="300-hz", nes_frequency=FAST_RATE, loop_tick=None),
        TestCase(label="300-hz-looping", nes_frequency=FAST_RATE, loop_tick=LOOP_TICK),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_every_store_lands_inside_the_vertical_blank(self, test_case: TestCase) -> None:
        run = frame_run(deck_song(test_case.nes_frequency, test_case.loop_tick))

        drawn = [write for write in run.stores if write.address in CELL_REGISTERS]
        assert {write.address for write in drawn} == set(CELL_REGISTERS)
        assert all(write.rendering for write in drawn)
        assert max(write.cycle for write in run.stores) < VERTICAL_BLANK_CYCLES

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_every_frame_s_work_ends_inside_the_frame(self, test_case: TestCase) -> None:
        run = frame_run(deck_song(test_case.nes_frequency, test_case.loop_tick))

        assert max(frame.cycles for frame in run.frames) < FRAME_CYCLES

    def test_the_frames_answering_the_controller_keep_their_budget(self) -> None:
        """Starting the song over clears the driver and starts it in the frame SELECT is read in."""
        console = booted(cartridge(deck_song(FAST_RATE, None), INFORMATION))

        frames = [console.frame(Button.START), *run_frames(console, PAUSED_FRAMES), console.frame(Button.SELECT)]
        frames.extend(run_frames(console, PAUSED_FRAMES))

        assert max(frame.cycles for frame in frames) < FRAME_CYCLES
        assert max(write.cycle for frame in frames for write in frame.video) < VERTICAL_BLANK_CYCLES


class TestTheDriverIsEnteredAtTheSameMomentOfEachFrame:
    """The interrupt does the same work before it plays the song, so each play call starts on the same cycle.

    The interrupt itself is taken once the instruction the main loop stands in completes, and the
    sprite transfer takes a cycle more where it begins on an odd one, which is all a frame's entry
    to the driver varies by.
    """

    @pytest.fixture
    def song(self) -> Song:
        return deck_song(NTSC_RATE, None)

    @pytest.fixture
    def arrivals(self, song: Song, driver_image: DriverImage, shell_image: ShellImage) -> List[Tuple[int, int]]:
        """The cycle each frame entered the interrupt on and the one it entered the driver's play routine on."""
        interrupt = shell_image.vectors[NMI_VECTOR_INDEX]
        play = driver_image.addresses.play
        run = frame_run(song, watched=frozenset({interrupt, play}))

        reached: List[Tuple[int, int]] = []
        for frame in run.frames:
            (entered,) = [arrival.cycle for arrival in frame.arrivals if arrival.address == interrupt]
            (played,) = [arrival.cycle for arrival in frame.arrivals if arrival.address == play]
            reached.append((entered, played))

        return reached

    def test_the_driver_is_played_once_every_frame(self, arrivals: List[Tuple[int, int]], song: Song) -> None:
        assert len(arrivals) == calls_through(song)

    def test_the_work_before_the_play_call_is_the_same_every_frame(self, arrivals: List[Tuple[int, int]]) -> None:
        work = [played - entered for entered, played in arrivals]

        assert max(work) - min(work) <= SPRITE_TRANSFER_ALIGNMENT_CYCLES

    def test_the_play_call_varies_by_the_interrupt_s_own_latency_alone(self, arrivals: List[Tuple[int, int]]) -> None:
        entered = [entry for entry, _ in arrivals]
        played = [play for _, play in arrivals]

        assert max(played) - min(played) <= max(entered) - min(entered) + SPRITE_TRANSFER_ALIGNMENT_CYCLES


class TestTheBootWaitsOutTheWarmUp:
    """For a stretch after power-on the picture processor ignores four of its registers.

    The shell's first stores switch the interrupt and the drawing off, which a console reset while
    running needs, and on power-on they land inside the warm-up, where the processor already
    stands with both off. Everything that draws the screen waits for the warm-up to end.
    """

    @pytest.fixture
    def run(self) -> FrameRun:
        return frame_run(deck_song(NTSC_RATE, None))

    def test_only_the_switching_off_lands_inside_the_warm_up(self, run: FrameRun) -> None:
        warming = [(write.address, write.value) for write in run.boot_stores if write.warming]

        assert warming == [
            (VideoRegister.CONTROL.address, SWITCHED_OFF),
            (VideoRegister.MASK.address, SWITCHED_OFF),
        ]

    def test_the_screen_is_drawn_after_the_warm_up_with_the_drawing_off(self, run: FrameRun) -> None:
        drawn = [write for write in run.boot_stores if write.address in CELL_REGISTERS]

        assert drawn
        assert not any(write.warming or write.rendering for write in drawn)

    def test_every_frame_after_the_boot_lands_past_the_warm_up(self, run: FrameRun) -> None:
        assert not any(write.warming for write in run.stores)
