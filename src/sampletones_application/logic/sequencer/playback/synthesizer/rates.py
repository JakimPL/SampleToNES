from dataclasses import dataclass
from typing import Self

from sampletones_core.project import Project
from sampletones_core.timing import TickClock


@dataclass(frozen=True)
class EngineRates:
    """The pair of rates a tick is sized from, held together so a change is one comparison.

    Each rate is owned elsewhere: the project states how many instructions the engine consumes
    each second, and whoever takes the audio states the rate it is rendered at — the output
    device for playback, the chosen format for a file. Together they fix how many samples one
    tick spans, so the synthesiser follows both.

    Attributes:
        nes_frequency: The engine ticks consumed each second.
        sample_rate: The samples the rendered audio holds each second.
    """

    nes_frequency: int
    sample_rate: int

    @classmethod
    def from_project(cls, project: Project, sample_rate: int) -> Self:
        """The rates in force for ``project`` rendered at ``sample_rate``."""
        return cls(
            nes_frequency=project.settings.nes_frequency,
            sample_rate=sample_rate,
        )

    def clock(self) -> TickClock:
        """The samples each tick spans under this pair of rates."""
        return TickClock.from_parameters(
            sample_rate=self.sample_rate,
            nes_frequency=self.nes_frequency,
        )
