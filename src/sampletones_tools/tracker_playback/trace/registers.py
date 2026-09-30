from dataclasses import dataclass
from typing import Dict, Final, Iterable, Mapping, Self

from sampletones_tools.player.trace.write import RegisterWrite

POWER_UP_VALUE: Final[int] = 0


@dataclass(frozen=True)
class ChipRegisters:
    """The value standing in each APU register once a run of writes has landed.

    A register keeps the last value written to it, so the registers on a tick are those the tick
    before left with the tick's own writes laid over them. That is what the chip plays from,
    whichever registers a player chose to write on the tick. A register never written stands at
    zero, the value the APU powers up with, which leaves every channel disabled.

    Attributes:
        values: The last value written to each register, by address.
    """

    values: Mapping[int, int]

    @classmethod
    def power_up(cls) -> Self:
        """The registers before any write lands."""
        return cls(values={})

    def written(self, writes: Iterable[RegisterWrite]) -> Self:
        """The registers once ``writes`` land on them, in order, a later write to a register replacing an earlier one.

        Args:
            writes: The writes, in the order the chip takes them.

        Returns:
            Self: The registers after the writes.
        """
        values: Dict[int, int] = dict(self.values)
        for write in writes:
            values[write.address] = write.value

        return type(self)(values=values)

    def value(self, address: int) -> int:
        """The value standing in one register.

        Args:
            address: The register.

        Returns:
            int: The last value written to it, or ``POWER_UP_VALUE`` for a register never written.
        """
        return self.values.get(address, POWER_UP_VALUE)
