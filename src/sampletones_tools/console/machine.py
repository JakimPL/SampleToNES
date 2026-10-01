from typing import Final, List, Optional, Tuple

from py65.devices.mpu6502 import MPU
from py65.memory import ObservableMemory

from sampletones_player.specification.nsf import HEADER_SIZE
from sampletones_player.specification.registers import (
    APU_FRAME_COUNTER,
    FIRST_CHANNEL_REGISTER,
)
from sampletones_tools.console.cartridge import Cartridge
from sampletones_tools.console.errors import RoutineOverrunError
from sampletones_tools.console.header import NSFHeader
from sampletones_tools.player.trace.trace import RegisterTrace
from sampletones_tools.player.trace.write import RegisterWrite

RETURN_SENTINEL: Final[int] = 0xFFF0
STACK_PAGE: Final[int] = 0x0100
STACK_TOP: Final[int] = 0xFF
ADDRESS_BITS: Final[int] = 8
LOW_BYTE: Final[int] = 0xFF
PLAY_ACCUMULATOR: Final[int] = 0x00
STEP_BUDGET: Final[int] = 1_000_000


class Console:
    """A 6502 running an NSF file the way an NSF player does, watching every APU register it writes.

    An NSF player maps the program behind the header, calls the init routine once with the song
    in the accumulator and the machine in X, and calls the play routine once per tick. This runs
    that sequence over py65's CPU with the APU's address range watched, so each routine answers
    with the writes it made. The memory and the APU start at zero, as at power-up.
    """

    def __init__(
        self,
        data: bytes,
        *,
        step_budget: int = STEP_BUDGET,
    ) -> None:
        """Loads an NSF file the way a player loads it.

        Args:
            data: The whole file, header included.
            step_budget: The most instructions a routine may run before it must return.

        Raises:
            NotAnNSFError: If the data opens with something other than the NSF signature.
            TruncatedDataError: If the data ends inside the header.
        """
        self.header = NSFHeader.read(data)
        self._step_budget = step_budget
        self._writes: List[RegisterWrite] = []
        self._memory = ObservableMemory()
        Cartridge(self.header, data[HEADER_SIZE:]).mount(self._memory)
        self._memory.subscribe_to_write(
            range(FIRST_CHANNEL_REGISTER, APU_FRAME_COUNTER + 1),
            self._observe,
        )
        self._processor = MPU(memory=self._memory)

    def initialize(self) -> Tuple[RegisterWrite, ...]:
        """Runs the init routine for the header's first song, on the machine the header names.

        Returns:
            Tuple[RegisterWrite, ...]: Every APU register the routine wrote, in order.

        Raises:
            RoutineOverrunError: If the routine runs past its step budget.
        """
        return self._call(
            self.header.init,
            accumulator=self.header.first_song_index,
            index=self.header.machine,
        )

    def play(self) -> Tuple[RegisterWrite, ...]:
        """Runs one play call, the way the player calls it each tick.

        Returns:
            Tuple[RegisterWrite, ...]: Every APU register the call wrote, in order.

        Raises:
            RoutineOverrunError: If the routine runs past its step budget.
        """
        return self._call(
            self.header.play,
            accumulator=PLAY_ACCUMULATOR,
            index=self.header.machine,
        )

    def trace(self, play_calls: int) -> RegisterTrace:
        """Runs a whole session: initialization followed by ``play_calls`` play calls.

        Args:
            play_calls: How many play calls the run covers.

        Returns:
            RegisterTrace: The writes of the initialization and of every play call.

        Raises:
            RoutineOverrunError: If a routine runs past its step budget.
        """
        initialization = self.initialize()
        return RegisterTrace(
            initialization=initialization,
            play_calls=tuple(self.play() for _ in range(play_calls)),
        )

    def _observe(self, address: int, value: int) -> Optional[int]:
        self._writes.append(RegisterWrite(address, value))
        return None

    def _seed_stack(self) -> None:
        """Leaves the sentinel on the stack as a return address, so a routine's final RTS lands on it."""
        returned = RETURN_SENTINEL - 1
        self._memory[STACK_PAGE + STACK_TOP] = returned >> ADDRESS_BITS
        self._memory[STACK_PAGE + STACK_TOP - 1] = returned & LOW_BYTE
        self._processor.sp = STACK_TOP - 2

    def _call(
        self,
        address: int,
        *,
        accumulator: int,
        index: int,
    ) -> Tuple[RegisterWrite, ...]:
        self._writes = []
        self._processor.a = accumulator
        self._processor.x = index
        self._seed_stack()
        self._processor.pc = address

        for _ in range(self._step_budget):
            if self._processor.pc == RETURN_SENTINEL:
                return tuple(self._writes)

            self._processor.step()

        raise RoutineOverrunError(
            f"The routine at {address:#06x} ran for {self._step_budget} instructions without returning"
        )
