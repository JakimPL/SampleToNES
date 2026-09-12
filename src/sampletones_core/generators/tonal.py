from abc import ABC
from typing import Dict, Tuple, TypeVar

from sampletones_core.configs import Config
from sampletones_core.constants.general import MAX_TIMER, MIN_TIMER
from sampletones_core.instructions import TonalInstruction
from sampletones_core.timers import PhaseTimer, frequency_to_timer, timer_to_frequency
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

    def sounds_at(self, pitch: int, offset: int) -> float:
        """The frequency in Hz this channel sounds a note at once a bend has moved it.

        A channel's waveform completes once per divider period times whatever the timer's own
        stride is, so this is where a divider becomes the pitch a listener hears — the triangle
        striding half as fast as the pulse and sounding an octave below the same divider.

        Args:
            pitch: The note the frame names.
            offset: The divider steps the frame is bent by.

        Returns:
            float: The frequency the channel sounds.
        """
        return timer_to_frequency(self.get_timer(pitch, offset)) * self.timer.phase_increment

    def bend_toward(self, pitch: int, frequency: float) -> int:
        """The bend that lands this note nearest a frequency, held inside the note's own room.

        A note owns half the dividers between itself and each neighbor, which is what tiles the
        whole divider range across the notes with none of it out of reach and none of it claimed
        twice. A frequency past that room takes the nearest bend the note offers, and the note
        beside it is the one that reaches further.

        Args:
            pitch: The note the frame names.
            frequency: The frequency in Hz the frame should sound at.

        Returns:
            int: The divider steps to bend by.
        """
        if frequency <= 0.0:
            return 0

        lowest, highest = self.bend_range(pitch)
        wanted = frequency_to_timer(frequency / self.timer.phase_increment) - self.timer_table[pitch]
        return int(clamp(wanted, lowest, highest))

    def bend_range(self, pitch: int) -> Tuple[int, int]:
        """The divider steps a bend may move a note, half the gap to each neighboring note.

        Args:
            pitch: The note the frame names.

        Returns:
            Tuple[int, int]: The lowest and highest bend the note offers.
        """
        divider = self.timer_table[pitch]
        below = self.timer_table.get(pitch - 1, divider + self._gap(pitch, pitch + 1))
        above = self.timer_table.get(pitch + 1, divider - self._gap(pitch - 1, pitch))
        return -((divider - above) // 2), (below - divider) // 2

    def _gap(self, lower: int, higher: int) -> int:
        """The dividers between two neighboring notes, where the table reaches both."""
        if lower not in self.timer_table or higher not in self.timer_table:
            return 0

        return self.timer_table[lower] - self.timer_table[higher]
