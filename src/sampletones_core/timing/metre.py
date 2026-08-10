from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from sampletones_core.project.settings import ProjectSettings


@dataclass(frozen=True)
class Metre:
    """The row grouping a pattern is felt in: its length, its beat, and the bar above it.

    ``first_highlight`` is the beat, the unit an actual tempo is read from, and
    ``second_highlight`` gathers beats into a bar. The bar is what organizes emphases
    where the beat divides the pattern unevenly; where both divide it cleanly the bar
    grouping agrees with the beats on their own.

    The pattern length is the hard limit, so a span reaching past the last row ends
    there and counts as the shorter span it is. This holds at both levels: a pattern of
    60 rows against a 16-row bar carries three whole bars and a 12-row one, and a bar
    shorter than its beat carries a single beat of the rows that remain.

    Attributes:
        rows: The pattern's row count.
        first_highlight: The rows one beat spans.
        second_highlight: The rows one bar spans.
    """

    rows: int
    first_highlight: int
    second_highlight: int

    def __post_init__(self) -> None:
        if self.rows < 1:
            raise ValueError(f"rows must be at least 1, got {self.rows}")

        if self.first_highlight < 1:
            raise ValueError(f"first_highlight must be at least 1, got {self.first_highlight}")

        if self.second_highlight < 1:
            raise ValueError(f"second_highlight must be at least 1, got {self.second_highlight}")

    @classmethod
    def from_settings(cls, settings: ProjectSettings, *, rows: int) -> Metre:
        """Reads the metre a project states, over a pattern of ``rows`` rows.

        The project holds the two highlights while the song holds the pattern length, so
        the row count arrives beside the settings.
        """
        return cls(
            rows=rows,
            first_highlight=settings.first_highlight,
            second_highlight=settings.second_highlight,
        )

    @property
    def spans(self) -> Tuple[Tuple[int, ...], ...]:
        """The whole grouping, as the beat row counts of each consecutive bar.

        Returns:
            Tuple[Tuple[int, ...], ...]: One entry per bar, each holding that bar's beat
                row counts in order, so the entries flattened come to ``rows``.
        """
        return tuple(
            self._divide(bar_rows, self.first_highlight)
            for bar_rows in self._divide(
                self.rows,
                self.second_highlight,
            )
        )

    @staticmethod
    def _divide(rows: int, unit: int) -> Tuple[int, ...]:
        """Cuts a row span into consecutive units, the final one holding what remains."""
        whole, remainder = divmod(rows, unit)
        spans = (unit,) * whole
        return spans + (remainder,) if remainder else spans
