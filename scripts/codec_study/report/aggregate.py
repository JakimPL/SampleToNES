from dataclasses import dataclass
from typing import Dict, Final, List, Sequence, Tuple

from codec_study.corpus.song import SongGroup
from codec_study.measure import Measurement

COLUMNS: Final[Tuple[str, ...]] = (
    "group",
    "variant",
    "songs",
    "ticks",
    "block",
    "bytes per tick",
    "change",
    "worst song",
    "seconds",
)


@dataclass(frozen=True)
class GroupRow:
    """One kind of song under one variant, summed over the songs of that kind.

    Attributes:
        group: Which kind of song it is.
        variant: The variant the encodings were built by.
        songs: How many songs the group holds.
        ticks: The ticks the songs last together.
        block: The bytes the song blocks take together.
        baseline: The bytes the same songs take under the baseline.
        worst: The largest growth any one song shows against its baseline, as a ratio.
        seconds: The processor time the encodings took together.
    """

    group: str
    variant: str
    songs: int
    ticks: int
    block: int
    baseline: int
    worst: float
    seconds: float

    @property
    def change(self) -> float:
        """How the group's bytes stand against the baseline, as a ratio; negative is smaller."""
        return self.block / self.baseline - 1.0

    @property
    def cells(self) -> Tuple[str, ...]:
        """The row as the table prints it, column by column."""
        return (
            self.group,
            self.variant,
            f"{self.songs}",
            f"{self.ticks}",
            f"{self.block}",
            f"{self.block / self.ticks:.3f}",
            f"{100.0 * self.change:+.1f}%",
            f"{100.0 * self.worst:+.1f}%",
            f"{self.seconds:.2f}",
        )


def group_rows(
    measurements: Sequence[Measurement],
    baseline: str,
) -> Tuple[GroupRow, ...]:
    """Sums the measurements over each kind of song, variant by variant.

    Args:
        measurements: Every song under every variant.
        baseline: The name of the variant the others are held against.

    Returns:
        Tuple[GroupRow, ...]: One row per kind of song and variant, kinds in their declared
            order and variants in the order they were measured.
    """
    reference: Dict[str, int] = {
        measurement.song.name: measurement.block for measurement in measurements if measurement.variant == baseline
    }
    variants = list(dict.fromkeys(measurement.variant for measurement in measurements))
    rows: List[GroupRow] = []
    for group in SongGroup:
        for variant in variants:
            chosen = [
                measurement
                for measurement in measurements
                if measurement.song.group is group and measurement.variant == variant
            ]
            if chosen:
                rows.append(_group_row(group, variant, chosen, reference))

    return tuple(rows)


def _group_row(
    group: SongGroup,
    variant: str,
    chosen: Sequence[Measurement],
    reference: Dict[str, int],
) -> GroupRow:
    return GroupRow(
        group=group.value,
        variant=variant,
        songs=len(chosen),
        ticks=sum(measurement.song.ticks for measurement in chosen),
        block=sum(measurement.block for measurement in chosen),
        baseline=sum(reference[measurement.song.name] for measurement in chosen),
        worst=max(measurement.block / reference[measurement.song.name] - 1.0 for measurement in chosen),
        seconds=sum(measurement.seconds for measurement in chosen),
    )
