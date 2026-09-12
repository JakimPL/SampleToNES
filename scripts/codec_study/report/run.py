import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Iterator, List, Optional, Sequence, Tuple

from codec_study.accounting import rows as accounting
from codec_study.manifest import StudyManifest
from codec_study.measure import Measurement
from codec_study.report import aggregate
from codec_study.report import rows as songs
from codec_study.report import verdicts
from codec_study.report.writers import markdown_table, write_csv
from codec_study.variants.production import BASELINE_NAME
from codec_study.variants.variant import Variant
from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_shared.paths.source import REPOSITORY_ROOT
from sampletones_shared.paths.user import USER_PATH_DOCUMENTS

DEFAULT_OUTPUT_ROOT: Final[Path] = USER_PATH_DOCUMENTS / "compression"
RUN_STAMP: Final[str] = "run-%Y%m%d-%H%M%S"
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
    directory = output or DEFAULT_OUTPUT_ROOT / datetime.now(UTC).strftime(RUN_STAMP)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def commit_hash() -> str:
    """The short hash of the commit the repository stands at, or a marker where git answers nothing."""
    completed = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPOSITORY_ROOT,
    )
    return completed.stdout.strip() or UNKNOWN_COMMIT


def write_run(
    directory: Path,
    manifest: StudyManifest,
    variants: Sequence[Variant],
    measurements: Sequence[Measurement],
    derived: Sequence[Measurement],
) -> None:
    """Writes a run's report, its verdicts, its accounting and the manifest that reproduces it.

    Args:
        directory: The run's directory.
        manifest: What the run read.
        variants: The variants every song was encoded under.
        measurements: Every song under every variant, in the order measured.
        derived: The strategy-depth measurements drawn from those, reported beside them and
            left out of the accounting, which reads each written encoding once.
    """
    reported = (*measurements, *derived)
    song_rows = [songs.study_row(measurement) for measurement in reported]
    group_rows = aggregate.group_rows(reported, BASELINE_NAME)
    verdict_rows = verdicts.verdict_rows(group_rows, measurements, variants)
    accounting_rows = [
        accounting.account(measurement, compressed) for measurement, compressed in _written(measurements)
    ]
    manifest.save(directory / MANIFEST_JSON)
    write_csv(directory / REPORT_CSV, songs.COLUMNS, [row.cells for row in song_rows])
    write_csv(directory / VERDICTS_CSV, verdicts.COLUMNS, [row.cells for row in verdict_rows])
    write_csv(directory / ACCOUNTING_CSV, accounting.COLUMNS, [row.cells for row in accounting_rows])
    lines = _header(manifest, variants)
    lines.extend(("## Variants", "", *_variants_table(variants), ""))
    lines.extend(
        (
            "## Verdicts",
            "",
            verdicts.RULE,
            "",
            *markdown_table(verdicts.COLUMNS, [row.cells for row in verdict_rows]),
            "",
        )
    )
    lines.extend(("## Groups", "", *markdown_table(aggregate.COLUMNS, [row.cells for row in group_rows]), ""))
    lines.extend(("## Songs", "", *markdown_table(songs.COLUMNS, [row.cells for row in song_rows]), ""))
    lines.extend(("## Accounting", "", *_accounting_table(accounting_rows), ""))
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
        f"Manifest: {MANIFEST_JSON}, {len(manifest.projects)} projects lengthened to "
        f"{manifest.lengthen_seconds} s, {len(manifest.reconstructions)} reconstruction sources",
        f"Variants: {named}",
        "",
        "Each accounting share is the saving a hypothesis would reach, as a share of the whole song block.",
        "",
    ]


def _variants_table(variants: Sequence[Variant]) -> List[str]:
    columns = ("variant", "hypothesis", "kind", "driver")
    cells = [(variant.name, variant.hypothesis, variant.kind.value, variant.note) for variant in variants]
    return markdown_table(columns, cells)


def _accounting_table(rows: Sequence[accounting.AccountingRow]) -> List[str]:
    columns = ("group", "song", "variant", "block", "dictionary", "idle bytes", "bend bytes")
    labels = tuple(f"{label} {name}" for label, name in accounting.HYPOTHESES)
    cells = [
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
    ]
    return markdown_table((*columns, *labels), cells)
