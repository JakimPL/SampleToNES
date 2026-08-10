from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from sampletones_core.project.settings import ProjectSettings
from sampletones_shared.constants.project import (
    REFERENCE_NES_FREQUENCY,
    REFERENCE_TEMPO,
)


@dataclass(frozen=True)
class RowRate:
    """How long one tracker row lasts, in engine ticks, as the exact ratio a tempo asks for.

    The engine advances a row once every ``ticks_per_row`` ticks of its ``nes_frequency``
    interrupt, and ``speed`` states that count directly at ``REFERENCE_TEMPO`` and
    ``REFERENCE_NES_FREQUENCY``, scaling from there with the tempo and the tick rate.

    The ratio is held exact, since a row rate is fractional for most tempi and the
    fraction is what a groove distributes across a pattern's rows.

    A row rate reads as a tempo in beats per minute once a metre says how many rows one
    beat spans::

        beats_per_minute = 60 * nes_frequency / (ticks_per_row * first_highlight)

    which at the four-row beat of common time comes to ``6 * tempo / speed``, the figure
    a tracker prints. The beat is therefore what turns a row rate into an actual tempo.

    Attributes:
        ticks_per_row: The exact number of engine ticks one row lasts.
    """

    ticks_per_row: Fraction

    @classmethod
    def from_parameters(
        cls,
        *,
        tempo: int,
        speed: int,
        nes_frequency: int,
    ) -> RowRate:
        """Derives the row rate from the three settings that govern it.

        Args:
            tempo: The project tempo.
            speed: Engine ticks per row at the reference tempo and tick rate.
            nes_frequency: The engine tick rate in Hz.

        Returns:
            RowRate: The exact ticks one row lasts under those settings.
        """
        return cls(
            ticks_per_row=Fraction(
                speed * nes_frequency * REFERENCE_TEMPO,
                tempo * REFERENCE_NES_FREQUENCY,
            ),
        )

    @classmethod
    def from_settings(cls, settings: ProjectSettings) -> RowRate:
        """Derives the row rate a project plays at.

        Args:
            settings: The project settings holding the tempo, the speed and the tick rate.

        Returns:
            RowRate: The exact ticks one row of this project lasts.
        """
        return cls.from_parameters(
            tempo=settings.tempo,
            speed=settings.speed,
            nes_frequency=settings.nes_frequency,
        )
