from dataclasses import dataclass
from typing import Self

from sampletones_core.project import Project

from .rates import EngineRates
from .timing import SongTiming


@dataclass(frozen=True)
class SongLength:
    """How long a song runs, in the units the audio it produces is measured in.

    Every row lasts the ticks the project's groove gives it, so a song's length is a whole
    number of engine ticks before a sample is rendered. The rates the audio is produced at
    turn those ticks into samples, which is the total a progress bar crosses and the duration
    a dialog projects.

    Attributes:
        ticks: The engine ticks the whole order lasts.
        rates: The engine and audio rates those ticks are rendered at.
    """

    ticks: int
    rates: EngineRates

    @classmethod
    def measure(cls, project: Project, *, sample_rate: int) -> Self:
        """The length ``project`` runs to when rendered at ``sample_rate``.

        Every pattern holds the song's row count, so one groove covers the whole order and the
        tick total is that groove's, once for each position the order plays.
        """
        groove = SongTiming.from_project(project).groove()
        return cls(
            ticks=project.song.order_length() * groove.total_ticks,
            rates=EngineRates.from_project(project, sample_rate),
        )

    @property
    def samples(self) -> int:
        """The samples the whole song holds at the rate it is rendered at."""
        return self.rates.clock().samples_at(self.ticks)
