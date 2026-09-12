from dataclasses import dataclass
from typing import Final, Tuple

from codec_study.measure import Measurement

COLUMNS: Final[Tuple[str, ...]] = (
    "group",
    "song",
    "variant",
    "ticks",
    "block",
    "bytes per tick",
    "dictionary",
    "streams",
    "phrases",
    "seconds",
    "lossless",
)


@dataclass(frozen=True)
class StudyRow:
    """One song measured under one variant, as the report prints it.

    Attributes:
        group: Which kind of song it is.
        song: The song's name.
        variant: The variant the encoding was built by.
        ticks: The ticks the song lasts.
        block: The bytes the whole song block takes.
        dictionary: The bytes the dictionary takes.
        streams: The bytes the streams take together.
        phrases: The phrases the dictionary holds.
        seconds: The processor time the encoding took.
        lossless: Whether the encoding plays back to its planes.
    """

    group: str
    song: str
    variant: str
    ticks: int
    block: int
    dictionary: int
    streams: int
    phrases: int
    seconds: float
    lossless: bool

    @property
    def cells(self) -> Tuple[str, ...]:
        """The row as the table prints it, column by column."""
        return (
            self.group,
            self.song,
            self.variant,
            f"{self.ticks}",
            f"{self.block}",
            f"{self.block / self.ticks:.3f}",
            f"{self.dictionary}",
            f"{self.streams}",
            f"{self.phrases}",
            f"{self.seconds:.2f}",
            "yes" if self.lossless else "no",
        )


def study_row(measurement: Measurement) -> StudyRow:
    """The report row of one measurement.

    Args:
        measurement: The encoding and its cost.

    Returns:
        StudyRow: The row.
    """
    return StudyRow(
        group=measurement.song.group.value,
        song=measurement.song.name,
        variant=measurement.variant,
        ticks=measurement.song.ticks,
        block=measurement.block,
        dictionary=measurement.dictionary,
        streams=measurement.streams,
        phrases=measurement.phrases,
        seconds=measurement.seconds,
        lossless=measurement.lossless,
    )
