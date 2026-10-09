import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Iterator, List, Optional, Sequence, Tuple

from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_shared.paths.source import REPOSITORY_ROOT
from sampletones_shared.paths.user import USER_PATH_DOCUMENTS
from sampletones_shared.utils.tables import Table
from sampletones_tools.checkout import is_checkout
from sampletones_tools.codec.study.accounting import rows as accounting
from sampletones_tools.codec.study.manifest import StudyManifest
from sampletones_tools.codec.study.measure import Measurement
from sampletones_tools.codec.study.plan import StudyPlan
from sampletones_tools.codec.study.report import aggregate
from sampletones_tools.codec.study.report import rows as songs
from sampletones_tools.codec.study.report import verdicts
from sampletones_tools.codec.study.variants.production import BASELINE_NAME
from sampletones_tools.codec.study.variants.variant import Variant
from sampletones_tools.runs import stamped_run_directory

OUTPUT_ROOT: Final[Path] = USER_PATH_DOCUMENTS / "compression"
REPORT_CSV: Final[str] = "report.csv"
REPORT_MARKDOWN: Final[str] = "report.md"
ACCOUNTING_CSV: Final[str] = "accounting.csv"
VERDICTS_CSV: Final[str] = "verdicts.csv"
MANIFEST_JSON: Final[str] = "manifest.json"
UNKNOWN_COMMIT: Final[str] = "unknown"


def run_directory(output: Optional[Path]) -> Path:
    """The directory a run writes into, created where it is missing.

    Args:
        output: The directory asked for, or ``None`` for a stamped one under the documents.

    Returns:
        Path: The directory.
    """
    directory = output or stamped_run_directory(OUTPUT_ROOT)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def commit_hash() -> str:
    """The short hash of the commit the checkout stands at, which dates the run's report.

    An installed copy has no checkout of its own around it, and a machine may run without git, so
    either records ``unknown``.
    """
    if not is_checkout(REPOSITORY_ROOT):
        return UNKNOWN_COMMIT

    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            cwd=REPOSITORY_ROOT,
        )
    except FileNotFoundError:
        return UNKNOWN_COMMIT

    return completed.stdout.strip() or UNKNOWN_COMMIT


def write_run(
    directory: Path,
    plan: StudyPlan,
    measurements: Sequence[Measurement],
    derived: Sequence[Measurement],
) -> None:
    """Writes a run's report, its verdicts, its accounting and the manifest that reproduces it.

    Args:
        directory: The run's directory.
        plan: What the run read and the variants every song was encoded under.
        measurements: Every song under every variant, in the order measured.
        derived: The strategy-depth measurements drawn from those, reported beside them and
            left out of the accounting, which reads each written encoding once.
    """
    reported = (*measurements, *derived)
    song_rows = [songs.study_row(measurement) for measurement in reported]
    group_rows = aggregate.group_rows(reported, BASELINE_NAME)
    verdict_rows = verdicts.verdict_rows(group_rows, measurements, plan.variants)
    accounting_rows = [
        accounting.account(measurement, compressed) for measurement, compressed in _written(measurements)
    ]
    song_table = Table(columns=songs.COLUMNS, rows=tuple(row.cells for row in song_rows))
    verdict_table = Table(columns=verdicts.COLUMNS, rows=tuple(row.cells for row in verdict_rows))
    plan.manifest.save(directory / MANIFEST_JSON)
    song_table.write_csv(directory / REPORT_CSV)
    verdict_table.write_csv(directory / VERDICTS_CSV)
    Table(columns=accounting.COLUMNS, rows=tuple(row.cells for row in accounting_rows)).write_csv(
        directory / ACCOUNTING_CSV
    )
    lines = _header(plan.manifest, plan.variants)
    lines.extend(("## Variants", "", *_variants_table(plan.variants).markdown_lines(), ""))
    lines.extend(("## Verdicts", "", verdicts.RULE, "", *verdict_table.markdown_lines(), ""))
    group_table = Table(columns=aggregate.COLUMNS, rows=tuple(row.cells for row in group_rows))
    lines.extend(("## Groups", "", *group_table.markdown_lines(), ""))
    lines.extend(("## Songs", "", *song_table.markdown_lines(), ""))
    lines.extend(("## Accounting", "", *_accounting_table(accounting_rows).markdown_lines(), ""))
    (directory / REPORT_MARKDOWN).write_text("\n".join(lines), encoding="utf-8")


def _written(measurements: Sequence[Measurement]) -> Iterator[Tuple[Measurement, CompressedPlanes]]:
    """The measurements whose streams the driver reads as they stand, beside those streams."""
    for measurement in measurements:
        written = measurement.encoding.written
        if written is not None:
            yield measurement, written


def _header(
    manifest: StudyManifest,
    variants: Sequence[Variant],
) -> List[str]:
    named = ", ".join(f"{variant.name} ({variant.kind.value})" for variant in variants)
    return [
        "# Compression study",
        "",
        f"Commit: {commit_hash()}",
        f"Date: {datetime.now(UTC).isoformat(timespec='seconds')}",
        (
            f"Manifest: {MANIFEST_JSON}, {len(manifest.projects)} projects lengthened to "
            f"{manifest.lengthen_seconds} s, {len(manifest.reconstructions)} reconstruction sources"
        ),
        f"Variants: {named}",
        "",
        "Each accounting share is the saving a hypothesis would reach, as a share of the whole song block.",
        "",
    ]


def _variants_table(variants: Sequence[Variant]) -> Table:
    columns = ("variant", "hypothesis", "kind", "driver")
    cells = tuple((variant.name, variant.hypothesis, variant.kind.value, variant.note) for variant in variants)
    return Table(columns=columns, rows=cells)


def _accounting_table(rows: Sequence[accounting.AccountingRow]) -> Table:
    columns = ("group", "song", "variant", "block", "dictionary", "idle bytes", "bend bytes")
    labels = tuple(f"{label} {name}" for label, name in accounting.HYPOTHESES)
    cells = tuple(
        (
            row.group,
            row.song,
            row.variant,
            f"{row.block}",
            row.share(row.dictionary),
            row.share(sum(plane.stream for plane in row.idle_planes)),
            row.share(sum(plane.stream for plane in row.planes if plane.bend)),
            *(row.share(finding.saving) for finding in row.findings),
        )
        for row in rows
    )
    return Table(columns=(*columns, *labels), rows=cells)
