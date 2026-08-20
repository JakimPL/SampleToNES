from typing import Dict, Final, List, Tuple

from py65.devices.mpu6502 import MPU
from py65.memory import ObservableMemory

from sampletones_player.driver.addresses import DriverAddresses
from sampletones_player.specification.nsf import HEADER_SIZE
from sampletones_player.specification.registers import (
    APU_FRAME_COUNTER,
    FIRST_CHANNEL_REGISTER,
)
from sampletones_player.trace.trace import RegisterTrace
from sampletones_player.trace.write import RegisterWrite

RETURN_SENTINEL: Final[int] = 0xFFF0
STACK_PAGE: Final[int] = 0x0100
STACK_TOP: Final[int] = 0xFF
FIRST_SONG_INDEX: Final[int] = 0x00
NTSC_MACHINE: Final[int] = 0x00
STEP_BUDGET: Final[int] = 1_000_000


class Console:
    """A 6502 running an exported file, watching every APU register the driver writes.

    An NSF player loads the image behind the header, calls the init routine once with the song
    number in the accumulator and the machine in X, and calls the play routine at the rate the
    header asks for. This runs the same sequence over py65's CPU with the APU's address range
    subscribed, so each routine answers with the writes it made. Capturing writes rather than
    sound is what lets a run stand against `RegisterTrace.from_song` value for value.
    """

    def __init__(self, data: bytes, addresses: DriverAddresses) -> None:
        """Loads an exported file the way a player loads it.

        Args:
            data: The whole `.nsf` file, header included.
            addresses: Where the image loads and which routines it answers at.
        """
        self._addresses = addresses
        self._writes: List[RegisterWrite] = []
        self._memory = ObservableMemory()
        self._memory.write(addresses.load, list(data[HEADER_SIZE:]))
        self._memory.subscribe_to_write(
            range(FIRST_CHANNEL_REGISTER, APU_FRAME_COUNTER + 1),
            self._observe,
        )
        self._processor = MPU(memory=self._memory)

    def _observe(self, address: int, value: int) -> None:
        self._writes.append(RegisterWrite(address, value))

    def _seed_stack(self) -> None:
        self._memory[STACK_PAGE + STACK_TOP] = (RETURN_SENTINEL - 1) >> 8
        self._memory[STACK_PAGE + STACK_TOP - 1] = (RETURN_SENTINEL - 1) & 0xFF
        self._processor.sp = STACK_TOP - 2

    def _call(self, address: int, accumulator: int) -> Tuple[RegisterWrite, ...]:
        self._writes = []
        self._processor.a = accumulator
        self._processor.x = NTSC_MACHINE
        self._seed_stack()
        self._processor.pc = address

        for _ in range(STEP_BUDGET):
            if self._processor.pc == RETURN_SENTINEL:
                return tuple(self._writes)

            self._processor.step()

        raise RuntimeError(f"the routine at {address:#06x} ran for {STEP_BUDGET} instructions without returning")

    def initialise(self) -> Tuple[RegisterWrite, ...]:
        """Runs the init routine, which readies the APU and sounds the song's first tick.

        Returns:
            Tuple[RegisterWrite, ...]: Every register the routine wrote, in order.
        """
        return self._call(self._addresses.init, FIRST_SONG_INDEX)

    def play(self) -> Tuple[RegisterWrite, ...]:
        """Runs one play call, the way the console calls it each frame.

        Returns:
            Tuple[RegisterWrite, ...]: Every register the call wrote, empty where the streams
                hold their tick through it.
        """
        return self._call(self._addresses.play, FIRST_SONG_INDEX)

    def trace(self, play_calls: int) -> RegisterTrace:
        """Runs a whole session: initialisation followed by ``play_calls`` play calls.

        Args:
            play_calls: How many play calls the run covers.

        Returns:
            RegisterTrace: The writes the driver made, grouped the way the model states them.
        """
        initialisation = self.initialise()
        return RegisterTrace(
            initialisation=initialisation,
            play_calls=tuple(self.play() for _ in range(play_calls)),
        )


def register_file(trace: RegisterTrace) -> List[Dict[int, int]]:
    """The APU as the driver leaves it after initialisation and after every call that sounds.

    A tick reaches the hardware as the values standing in the registers once its writes land, and
    the three registers written only on change keep the value an earlier tick left there. Reading
    the whole file back after each sounding call is therefore what recovers a tick's full state
    from a trace that states only what changed.

    Args:
        trace: The writes a run of the driver made.

    Returns:
        List[Dict[int, int]]: One register file per tick the run sounded, in order.
    """
    registers: Dict[int, int] = {}
    ticks: List[Dict[int, int]] = []

    for writes in (trace.initialisation, *trace.play_calls):
        if not writes:
            continue

        for write in writes:
            registers[write.address] = write.value

        ticks.append(dict(registers))

    return ticks
