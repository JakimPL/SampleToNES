from abc import ABC
from typing import Dict, TypeVar

from sampletones_core.configs import Config
from sampletones_core.constants.general import MAX_TIMER, MIN_TIMER
from sampletones_core.instructions import TonalInstruction
from sampletones_core.timers import PhaseTimer, frequency_to_timer
from sampletones_shared.utils.arrays import clamp

from .generator import Generator

TonalInstructionT = TypeVar("TonalInstructionT", bound=TonalInstruction)


class TonalGenerator(Generator[TonalInstructionT, PhaseTimer], ABC):
    """A generator whose channel names a note, reached by loading a divider.

    The pulse and triangle channels sound a pitch the same way — the note resolves to a divider,
    and the frame's own bend moves it from there — so both read one table and drive their timer
    through one call. The divider stays inside the range the register holds and away from the
    value that stops the waveform, which keeps a bend audible wherever it lands.
    """

    def __init__(self, config: Config, name: str) -> None:
        super().__init__(config, name)
        self.timer_table: Dict[int, int] = {
            pitch: frequency_to_timer(frequency) for pitch, frequency in self.frequency_table.items()
        }

    def set_timer(self, instruction: TonalInstructionT) -> None:
        if instruction.on:
            self.timer.timer = self.get_timer(instruction.pitch, instruction.timer_offset)
        else:
            self.timer.frequency = 0.0

    def get_timer(self, pitch: int, offset: int) -> int:
        """The divider a note sounds at once the frame's bend has moved it.

        Args:
            pitch: The note the frame names.
            offset: The divider steps the frame is bent by.

        Returns:
            int: The divider to run at, within the range the register holds.

        Raises:
            KeyError: If the pitch is absent from the generator's tables.
        """
        return int(clamp(self.timer_table[pitch] + offset, MIN_TIMER, MAX_TIMER))
