from dataclasses import dataclass
from typing import NamedTuple, Tuple

from sampletones_tools.console.rom.write import VideoWrite
from sampletones_tools.player.trace.write import RegisterWrite


class Arrival(NamedTuple):
    """One time the program reached an address the console was asked to watch.

    Attributes:
        address: The watched address the program counter stood at.
        cycle: The CPU cycle it stood there on, counted from the start of the frame.
    """

    address: int
    cycle: int


@dataclass(frozen=True)
class Frame:
    """What a program did between one vertical blank and the next.

    Attributes:
        sound: Every APU register the program wrote, in order.
        video: Every store the program made to the picture processor, in order.
        arrivals: Every time the program reached a watched address, in order.
        cycles: The CPU cycles the frame's work took, counted from the start of the frame to the
            moment the program came to rest waiting for the next one. A program still working when
            the frame ended answers with the whole frame.
    """

    sound: Tuple[RegisterWrite, ...]
    video: Tuple[VideoWrite, ...]
    arrivals: Tuple[Arrival, ...]
    cycles: int
