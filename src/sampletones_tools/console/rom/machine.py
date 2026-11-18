from typing import AbstractSet, Dict, Final, FrozenSet, List, Optional, Sequence, Tuple

from py65.devices.mpu6502 import MPU
from py65.memory import ObservableMemory

from sampletones_player.specification.memory import RAM_SIZE
from sampletones_player.specification.nsf import PROGRAM_START
from sampletones_player.specification.registers import (
    APU_FRAME_COUNTER,
    APU_STATUS,
    FIRST_CHANNEL_REGISTER,
    LAST_CHANNEL_REGISTER,
)
from sampletones_player.specification.rom import ROM_HEADER_SIZE
from sampletones_tools.console.rom.cartridge import ROMCartridge
from sampletones_tools.console.rom.controller import NO_BUTTONS, Button, Controller
from sampletones_tools.console.rom.errors import BootOverrunError, ConsoleStateError
from sampletones_tools.console.rom.frame import Arrival, Frame
from sampletones_tools.console.rom.header import ROMHeader
from sampletones_tools.console.rom.registers import (
    FIRST_CONTROLLER,
    INPUT_OUTPUT_END,
    INPUT_OUTPUT_START,
    OPEN_BUS,
    PAGE_SIZE,
    RAM_MIRRORS_END,
    SECOND_CONTROLLER,
    SPRITE_TRANSFER,
    VIDEO_REGISTERS_END,
    VIDEO_REGISTERS_START,
    VideoRegister,
)
from sampletones_tools.console.rom.screen import Screen
from sampletones_tools.console.rom.timing import (
    DOTS_PER_CYCLE,
    DOTS_PER_FRAME,
    FIRST_VERTICAL_BLANK_DOTS,
    SPRITE_TRANSFER_ALIGNMENT_CYCLES,
    SPRITE_TRANSFER_CYCLES,
    VERTICAL_BLANK_DOTS,
    WARM_UP_CYCLES,
)
from sampletones_tools.console.rom.video import Video
from sampletones_tools.console.rom.write import VideoWrite
from sampletones_tools.player.trace.trace import RegisterTrace
from sampletones_tools.player.trace.write import RegisterWrite

ADDRESS_SPACE: Final[int] = 0x10000
EMPTY_BYTE: Final[int] = 0x00
POWER_ON_DOTS: Final[int] = 0
STEP_BUDGET: Final[int] = 1_000_000
SKIP_IDLE_LOOPS: Final[bool] = True
NOTHING_WATCHED: Final[FrozenSet[int]] = frozenset()
SOUND_REGISTERS: Final[Tuple[int, ...]] = (
    *range(FIRST_CHANNEL_REGISTER, LAST_CHANNEL_REGISTER + 1),
    APU_STATUS,
    APU_FRAME_COUNTER,
)

ProcessorState = Tuple[int, int, int, int, int, int]


class ROMConsole:
    """A console running a cartridge image from its reset vector, frame by frame.

    The program runs on py65's CPU against a register-level picture processor, a controller and
    the cartridge's ROM, with every APU register it writes watched. Time is counted in the
    processor's own cycles and held against the NTSC frame: the vertical blank flag is set once
    every 341 by 262 dots, the interrupt follows it where the program asked for one, and each
    store to the picture processor is stamped with the cycle it completes on.

    The power-on state is the caller's to choose, since a console's memory starts as whatever it
    held. A program that depends on cleared memory shows it once it boots from anything else.

    A program between two frames usually waits in a loop of plain memory reads. The console
    proves that: a CPU state met twice, with every access between the two a plain memory read,
    repeats until the next interrupt. It then moves the clock on by whole turns of that loop and
    steps the rest, which leaves every later instruction on the cycle it would have reached step
    by step. Reaching a watched address counts against that proof, so a loop passing one is
    stepped in full and each arrival is recorded.

    The picture's own timing stays outside the model: every frame has the length of a frame drawn
    with rendering off, and the sprite-zero and overflow flags read as clear.
    """

    def __init__(
        self,
        data: bytes,
        *,
        memory: Sequence[int],
        watched: AbstractSet[int] = NOTHING_WATCHED,
        step_budget: int = STEP_BUDGET,
        skip_idle_loops: bool = SKIP_IDLE_LOOPS,
    ) -> None:
        """Maps a cartridge image the way a console does and stands the CPU on its reset vector.

        Args:
            data: The whole file, header included.
            memory: The 2 KB the console's memory holds at power-on.
            watched: The addresses whose every arrival a frame records.
            step_budget: The most instructions the boot may run before the program switches its
                frame interrupt on.
            skip_idle_loops: Whether the clock moves over the turns of a loop proven idle. Stepping
                every turn takes longer and plays the same frames.

        Raises:
            NotAROMError: If the data opens with something other than the iNES signature.
            TruncatedDataError: If the data ends inside the header, the program or the patterns.
            UnsupportedCartridgeError: If the header names a board other than NROM.
            ValueError: If ``memory`` holds anything but the console's 2 KB.
        """
        if len(memory) != RAM_SIZE:
            raise ValueError(f"The console holds {RAM_SIZE} bytes of memory, and {len(memory)} were given")

        self.header = ROMHeader.read(data)
        cartridge = ROMCartridge(self.header, data[ROM_HEADER_SIZE:])
        self._watched = watched
        self._step_budget = step_budget
        self._skip_idle_loops = skip_idle_loops

        self._held: List[int] = [EMPTY_BYTE] * ADDRESS_SPACE
        for mirror in range(0, RAM_MIRRORS_END, RAM_SIZE):
            self._held[mirror : mirror + RAM_SIZE] = list(memory)

        self._memory = ObservableMemory(subject=self._held)
        cartridge.mount(self._memory)
        self._video = Video(cartridge.patterns, cartridge.mirroring)
        self._controller = Controller()
        self._subscribe()
        self._processor = MPU(memory=self._memory, pc=None)

        self._booted = False
        self._frame_start = POWER_ON_DOTS
        self._boundary = FIRST_VERTICAL_BLANK_DOTS
        self._blank_end: Optional[int] = None
        self._landing = 0
        self._charged = 0
        self._sound: List[RegisterWrite] = []
        self._stores: List[VideoWrite] = []
        self._arrivals: List[Arrival] = []
        self._seen: Dict[ProcessorState, int] = {}
        self._rested: Optional[int] = None

    @property
    def screen(self) -> Screen:
        """What the picture processor holds for the picture it draws next."""
        return self._video.screen

    def boot(self) -> Tuple[Frame, ...]:
        """Runs the program from reset through the frame in which it switches its frame interrupt on.

        A program waits out the picture processor's warm-up before it sets anything up, so the
        boot spans several vertical blanks. Each stretch between two of them comes back as a frame
        of its own, the first counted from reset.

        Returns:
            Tuple[Frame, ...]: What the program did in each stretch, in order.

        Raises:
            BootOverrunError: If the program spends its step budget, or comes to rest, with the
                frame interrupt still off.
            ConsoleStateError: If the console has booted already.
            ReadOnlyMemoryError: If the program stores a byte into the cartridge's ROM.
        """
        if self._booted:
            raise ConsoleStateError("The console boots once, from power-on")

        frames: List[Frame] = []
        steps = 0
        while True:
            steps += self._run()
            frames.append(self._close_frame())
            if self._video.interrupts:
                break

            if self._rested is not None:
                raise BootOverrunError("The program came to rest with its frame interrupt off")

            if steps > self._step_budget:
                raise BootOverrunError(f"The program ran for {steps} instructions and left its frame interrupt off")

            self._begin_frame()

        self._booted = True
        return tuple(frames)

    def frame(self, buttons: Button) -> Frame:
        """Runs one frame: the vertical blank begins, the interrupt is delivered, and the program runs to the next.

        Args:
            buttons: The controller buttons held down through the frame.

        Returns:
            Frame: What the program did in the frame.

        Raises:
            ConsoleStateError: If the console has yet to boot.
            ReadOnlyMemoryError: If the program stores a byte into the cartridge's ROM.
        """
        if not self._booted:
            raise ConsoleStateError("A frame runs on a console that has booted")

        self._controller.hold(buttons)
        self._begin_frame()
        self._run()
        return self._close_frame()

    def trace(self, play_calls: int) -> RegisterTrace:
        """Runs a whole session: the boot followed by ``play_calls`` frames with no button held.

        The APU writes of the boot stand where an NSF's initialization stands, and each frame's
        stand where a play call's do, so a cartridge is held to the same statement an NSF is.

        Args:
            play_calls: How many frames the run covers behind the boot.

        Returns:
            RegisterTrace: The writes of the boot and of every frame.

        Raises:
            BootOverrunError: If the program never switches its frame interrupt on.
            ConsoleStateError: If the console has booted already.
        """
        initialization = tuple(write for frame in self.boot() for write in frame.sound)
        return RegisterTrace(
            initialization=initialization,
            play_calls=tuple(self.frame(NO_BUTTONS).sound for _ in range(play_calls)),
        )

    def _subscribe(self) -> None:
        memory = self._memory
        memory.subscribe_to_write(range(0, RAM_MIRRORS_END), self._store_memory)
        memory.subscribe_to_write(range(RAM_MIRRORS_END, PROGRAM_START), self._disturb)
        memory.subscribe_to_write(range(VIDEO_REGISTERS_START, VIDEO_REGISTERS_END), self._store_video)
        memory.subscribe_to_read(range(VIDEO_REGISTERS_START, VIDEO_REGISTERS_END), self._load_video)
        memory.subscribe_to_write(SOUND_REGISTERS, self._store_sound)
        memory.subscribe_to_write((SPRITE_TRANSFER,), self._transfer_sprites)
        memory.subscribe_to_write((FIRST_CONTROLLER,), self._strobe)
        memory.subscribe_to_read(range(INPUT_OUTPUT_START, INPUT_OUTPUT_END), self._load_input)

    def _begin_frame(self) -> None:
        self._frame_start = self._boundary
        self._boundary += DOTS_PER_FRAME
        self._blank_end = self._frame_start + VERTICAL_BLANK_DOTS
        self._video.begin_vertical_blank()
        if self._video.take_interrupt():
            self._processor.nmi()

    def _close_frame(self) -> Frame:
        ended = self._rested if self._rested is not None else self._processor.processorCycles
        frame = Frame(
            sound=tuple(self._sound),
            video=tuple(self._stores),
            arrivals=tuple(self._arrivals),
            cycles=self._elapsed(ended),
        )
        self._sound = []
        self._stores = []
        self._arrivals = []
        self._seen.clear()
        return frame

    def _run(self) -> int:
        """Runs the program to the next vertical blank, answering with the instructions it stepped."""
        processor = self._processor
        self._rested = None
        steps = 0
        while processor.processorCycles * DOTS_PER_CYCLE < self._boundary:
            if self._rested is None:
                self._look_for_rest()

            self._step()
            steps += 1

        return steps

    def _step(self) -> None:
        processor = self._processor
        if processor.pc in self._watched:
            self._arrivals.append(Arrival(processor.pc, self._elapsed(processor.processorCycles)))
            self._seen.clear()

        self._landing = processor.processorCycles + processor.cycletime[self._held[processor.pc]]
        processor.step()
        if self._charged:
            processor.processorCycles += self._charged
            self._charged = 0

        if self._video.take_interrupt():
            processor.nmi()

        self._pass_time()

    def _look_for_rest(self) -> None:
        """Holds the CPU state against every one met since the last store, and skips the turns of a loop it proves."""
        processor = self._processor
        state = (processor.pc, processor.a, processor.x, processor.y, processor.sp, processor.p)
        first = self._seen.get(state)
        if first is None:
            self._seen[state] = processor.processorCycles
            return

        self._rested = first
        if not self._skip_idle_loops:
            return

        turn = (processor.processorCycles - first) * DOTS_PER_CYCLE
        remaining = self._boundary - processor.processorCycles * DOTS_PER_CYCLE
        processor.processorCycles += ((remaining - 1) // turn) * turn // DOTS_PER_CYCLE
        self._pass_time()

    def _pass_time(self) -> None:
        cycles = self._processor.processorCycles
        if self._video.warming and cycles >= WARM_UP_CYCLES:
            self._video.finish_warming()

        if self._blank_end is not None and cycles * DOTS_PER_CYCLE >= self._blank_end:
            self._video.end_vertical_blank()
            self._blank_end = None

    def _elapsed(self, cycles: int) -> int:
        """The CPU cycles between the start of the frame and a moment on the processor's own count."""
        return (cycles * DOTS_PER_CYCLE - self._frame_start) // DOTS_PER_CYCLE

    def _record(self, address: int, value: int) -> None:
        self._seen.clear()
        self._stores.append(
            VideoWrite(
                address=address,
                value=value,
                cycle=self._elapsed(self._landing),
                rendering=self._video.rendering,
                warming=self._video.warming,
            )
        )

    def _disturb(self, address: int, value: int) -> None:  # pylint: disable=unused-argument
        self._seen.clear()

    def _store_memory(self, address: int, value: int) -> None:
        self._seen.clear()
        for mirror in range(address % RAM_SIZE, RAM_MIRRORS_END, RAM_SIZE):
            self._held[mirror] = value

    def _store_video(self, address: int, value: int) -> None:
        register = VideoRegister.at(address)
        self._record(register.address, value)
        self._video.write(register, value)

    def _load_video(self, address: int) -> int:
        self._seen.clear()
        return self._video.read(VideoRegister.at(address))

    def _store_sound(self, address: int, value: int) -> None:
        self._sound.append(RegisterWrite(address, value))

    def _transfer_sprites(self, address: int, value: int) -> None:
        self._record(address, value)
        page = value * PAGE_SIZE
        self._video.transfer(self._held[page : page + PAGE_SIZE])
        aligned = self._landing % 2 == 0
        self._charged = SPRITE_TRANSFER_CYCLES + (0 if aligned else SPRITE_TRANSFER_ALIGNMENT_CYCLES)

    def _strobe(self, address: int, value: int) -> None:  # pylint: disable=unused-argument
        self._controller.write(value)

    def _load_input(self, address: int) -> Optional[int]:
        self._seen.clear()
        if address == FIRST_CONTROLLER:
            return self._controller.read()

        if address == SECOND_CONTROLLER:
            return OPEN_BUS

        return None
