from dataclasses import dataclass
from typing import Self

from sampletones_core.project import Project
from sampletones_core.timing.bounds import MAX_TICKS_PER_ROW, MIN_TICKS_PER_ROW
from sampletones_core.timing.groove import Groove, calculate_groove
from sampletones_core.timing.metre import Metre
from sampletones_core.timing.rate import RowRate


@dataclass(frozen=True)
class SongTiming:
    """Everything a project's groove is built from, held together so a change is one comparison.

    Attributes:
        rate: The exact ticks one row lasts under the project's tempo, speed and tick rate.
        metre: The pattern length and the beat and bar grouping the ticks are spread over.
    """

    rate: RowRate
    metre: Metre

    @classmethod
    def from_project(cls, project: Project) -> Self:
        """Reads the timing a project plays at, taking the pattern length from its song."""
        return cls(
            rate=RowRate.from_settings(project.settings),
            metre=Metre.from_settings(
                project.settings,
                rows=project.song.rows_per_pattern,
            ),
        )

    def groove(self) -> Groove:
        """Spreads the row rate across a pattern's rows.

        A song runs at whatever tempo the project states, so the one bound that applies is that
        every row lasts at least a tick and keeps sounding; the ceiling is the slowest row the
        settings can ask for, which leaves the groove free to realize the rate exactly.
        """
        return calculate_groove(
            self.rate,
            self.metre,
            minimum_ticks=MIN_TICKS_PER_ROW,
            maximum_ticks=MAX_TICKS_PER_ROW,
        )
