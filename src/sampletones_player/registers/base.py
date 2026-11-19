from abc import ABC, abstractmethod
from typing import Tuple

from pydantic import BaseModel, ConfigDict


class ChannelRegisters(BaseModel, ABC):
    """The register values one channel writes for a single engine tick.

    The driver interprets nothing: it moves these bytes to the addresses its channel owns.
    Every rule the hardware follows — how a duty cycle reaches its bits, which value silences
    a channel, how a pitch becomes a period — is settled here, where it is testable.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    @property
    @abstractmethod
    def values(self) -> Tuple[int, ...]:
        """The tick's register values, in the order the driver writes them.

        Returns:
            Tuple[int, ...]: One value per register the channel writes each tick.
        """

    @property
    def written(self) -> Tuple[int, ...]:
        """The values the driver writes for the tick: the leading registers of :attr:`values`.

        A channel writes every register it owns unless its own rule leaves the later ones standing.
        """
        return self.values
