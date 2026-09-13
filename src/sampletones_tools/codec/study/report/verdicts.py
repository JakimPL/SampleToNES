from dataclasses import dataclass
from enum import StrEnum
from typing import Dict, Final, List, Optional, Sequence, Tuple

from sampletones_tools.codec.study.corpus.song import SongGroup
from sampletones_tools.codec.study.measure import Measurement
from sampletones_tools.codec.study.report.aggregate import GroupRow
from sampletones_tools.codec.study.variants.variant import Variant, VariantKind

PROJECT_BAR: Final[float] = 0.03
RECONSTRUCTION_BAR: Final[float] = 0.05
REGRESSION_BAR: Final[float] = 0.01
PROJECT_GROUPS: Final[Tuple[SongGroup, ...]] = (SongGroup.PROJECT, SongGroup.LONG_PROJECT)
UNMEASURED: Final[str] = ""
COLUMNS: Final[Tuple[str, ...]] = (
    "variant",
    "hypothesis",
    "kind",
    "projects",
    "reconstructions",
    "worst song",
    "verdict",
)
RULE: Final[str] = (
    f"A variant graduates when it saves {100 * PROJECT_BAR:.0f}% over the projects, short and "
    f"lengthened together, or {100 * RECONSTRUCTION_BAR:.0f}% over the reconstructions, with no song "
    f"growing by more than {100 * REGRESSION_BAR:.0f}%. A variant priced at token level is provisional "
    "until its production layer confirms the figure."
)


class Verdict(StrEnum):
    """What the decision rule says of a variant.

    Attributes:
        GRADUATES: The variant saves enough, harms no song, and its bytes are the driver's.
        PROVISIONAL: The variant saves enough and harms no song, priced at token level.
        REJECTED: The variant saves too little, or grows a song past the bar.
    """

    GRADUATES = "graduates"
    PROVISIONAL = "provisional"
    REJECTED = "rejected"


@dataclass(frozen=True)
class VerdictRow:
    """One variant judged by the decision rule.

    Attributes:
        variant: The variant's name.
        hypothesis: The hypothesis the variant measures.
        kind: What the variant changes.
        projects: How the projects' bytes stand against the baseline, short and lengthened
            together, as a ratio; ``None`` where the variant measured none.
        reconstructions: The same over the reconstructions.
        worst: The largest growth any one song shows against its baseline, as a ratio.
        verdict: What the rule says.
    """

    variant: str
    hypothesis: str
    kind: VariantKind
    projects: Optional[float]
    reconstructions: Optional[float]
    worst: float
    verdict: Verdict

    @property
    def cells(self) -> Tuple[str, ...]:
        """The row as the table prints it, column by column."""
        return (
            self.variant,
            self.hypothesis,
            self.kind.value,
            _percent(self.projects),
            _percent(self.reconstructions),
            f"{100.0 * self.worst:+.1f}%",
            self.verdict.value,
        )


def _percent(change: Optional[float]) -> str:
    return UNMEASURED if change is None else f"{100.0 * change:+.1f}%"


def _change(rows: Sequence[GroupRow]) -> Optional[float]:
    if not rows:
        return None

    return sum(row.block for row in rows) / sum(row.baseline for row in rows) - 1.0


def _earned(
    projects: Optional[float],
    reconstructions: Optional[float],
) -> bool:
    over_projects = projects is not None and projects <= -PROJECT_BAR
    over_reconstructions = reconstructions is not None and reconstructions <= -RECONSTRUCTION_BAR
    return over_projects or over_reconstructions


def judge(
    projects: Optional[float],
    reconstructions: Optional[float],
    worst: float,
    *,
    priced: bool,
) -> Verdict:
    """Applies the decision rule to one variant's aggregates.

    Args:
        projects: The change over the projects, short and lengthened together.
        reconstructions: The change over the reconstructions.
        worst: The largest growth any one song shows.
        priced: Whether the variant's bytes were priced at token level.

    Returns:
        Verdict: What the rule says.
    """
    if worst > REGRESSION_BAR or not _earned(projects, reconstructions):
        return Verdict.REJECTED

    return Verdict.PROVISIONAL if priced else Verdict.GRADUATES


def verdict_rows(
    group_rows: Sequence[GroupRow],
    measurements: Sequence[Measurement],
    variants: Sequence[Variant],
) -> Tuple[VerdictRow, ...]:
    """Judges every variant the run measured, the baseline excepted.

    Args:
        group_rows: The measurements summed over each kind of song, variant by variant.
        measurements: Every song under every variant.
        variants: The variants the run encoded under.

    Returns:
        Tuple[VerdictRow, ...]: One row per measured variant, in the order given.
    """
    by_variant: Dict[str, List[GroupRow]] = {}
    for row in group_rows:
        by_variant.setdefault(row.variant, []).append(row)

    priced = {measurement.variant for measurement in measurements if measurement.encoding.written is None}
    rows: List[VerdictRow] = []
    for variant in variants:
        if variant.kind is VariantKind.BASELINE or variant.name not in by_variant:
            continue

        rows.append(_verdict_row(variant, by_variant[variant.name], priced=variant.name in priced))

    return tuple(rows)


def _verdict_row(
    variant: Variant,
    rows: Sequence[GroupRow],
    *,
    priced: bool,
) -> VerdictRow:
    projects = _change([row for row in rows if SongGroup(row.group) in PROJECT_GROUPS])
    reconstructions = _change([row for row in rows if SongGroup(row.group) is SongGroup.RECONSTRUCTION])
    worst = max(row.worst for row in rows)
    return VerdictRow(
        variant=variant.name,
        hypothesis=variant.hypothesis,
        kind=variant.kind,
        projects=projects,
        reconstructions=reconstructions,
        worst=worst,
        verdict=judge(projects, reconstructions, worst, priced=priced),
    )
