import csv
from pathlib import Path
from typing import Final, List

from sampletones_shared.utils.tables import Table
from sampletones_tools.calibration.report import (
    CSV_COLUMNS,
    MEAN_COLUMN,
    REPORT_TITLE,
    VARIANT_COLUMN,
    write_csv,
    write_markdown,
)
from sampletones_tools.calibration.rows import CalibrationRow

ROWS: Final[List[CalibrationRow]] = [
    CalibrationRow(
        variant="fft",
        item="tone-a",
        family="sines",
        category="tones",
        referee="spectral",
        component="score",
        score=0.25,
    ),
    CalibrationRow(
        variant="fft",
        item="tone-b",
        family="sines",
        category="tones",
        referee="spectral",
        component="score",
        score=0.75,
    ),
    CalibrationRow(
        variant="fft", item="hiss", family="tones", category="noise", referee="spectral", component="score", score=1.0
    ),
    CalibrationRow(
        variant="cqt", item="tone-a", family="sines", category="tones", referee="spectral", component="score", score=0.5
    ),
    CalibrationRow(
        variant="cqt", item="hiss", family="tones", category="noise", referee="spectral", component="score", score=0.5
    ),
    CalibrationRow(
        variant="fft", item="tone-a", family="sines", category="tones", referee="envelope", component="score", score=2.0
    ),
    CalibrationRow(
        variant="fft", item="tone-a", family="sines", category="tones", referee="envelope", component="added", score=1.5
    ),
]


class TestWriteCsv:
    def test_every_row_reads_back_under_the_columns(self, tmp_path: Path) -> None:
        path = tmp_path / "report.csv"

        write_csv(ROWS, path)

        with path.open(newline="", encoding="utf-8") as handle:
            header, *cells = list(csv.reader(handle))
        assert tuple(header) == CSV_COLUMNS
        assert [(*row[:6], float(row[6])) for row in cells] == [
            (row.variant, row.item, row.family, row.category, row.referee, row.component, row.score) for row in ROWS
        ]


class TestWriteMarkdown:
    def test_each_family_pivots_every_referee_s_score_then_every_further_reading(self, tmp_path: Path) -> None:
        path = tmp_path / "report.md"

        write_markdown(ROWS, path)

        lines = path.read_text(encoding="utf-8").split("\n")
        sines = Table(
            columns=(VARIANT_COLUMN, "tones", MEAN_COLUMN),
            rows=(("fft", "0.500", "0.500"), ("cqt", "0.500", "0.500")),
        )
        tones = Table(
            columns=(VARIANT_COLUMN, "noise", MEAN_COLUMN),
            rows=(("fft", "1.000", "1.000"), ("cqt", "0.500", "0.500")),
        )
        envelope = Table(columns=(VARIANT_COLUMN, "tones", MEAN_COLUMN), rows=(("fft", "2.000", "2.000"),))
        added = Table(columns=(VARIANT_COLUMN, "tones", MEAN_COLUMN), rows=(("fft", "1.500", "1.500"),))
        assert lines == [
            REPORT_TITLE,
            "",
            "## sines",
            "",
            "### spectral",
            "",
            *sines.markdown_lines(),
            "",
            "### envelope",
            "",
            *envelope.markdown_lines(),
            "",
            "#### added",
            "",
            *added.markdown_lines(),
            "",
            "## tones",
            "",
            "### spectral",
            "",
            *tones.markdown_lines(),
            "",
        ]


def _row(variant: str, item: str, category: str, score: float) -> CalibrationRow:
    return CalibrationRow(
        variant=variant,
        item=item,
        family="sines",
        category=category,
        referee="spectral",
        component="score",
        score=score,
    )


def _table_lines(rows: List[CalibrationRow], tmp_path: Path) -> List[str]:
    """The lines of the one table a family of one referee's score reports."""
    path = tmp_path / "report.md"
    write_markdown(rows, path)
    lines = path.read_text(encoding="utf-8").split("\n")
    return lines[6:-1]


class TestPivot:
    def test_the_mean_weighs_every_sound_alike_whatever_its_category(self, tmp_path: Path) -> None:
        rows = [*(_row("fft", f"tone-{index}", "tones", 1.0) for index in range(3)), _row("fft", "hiss", "noise", 5.0)]

        table = Table(
            columns=(VARIANT_COLUMN, "tones", "noise", MEAN_COLUMN), rows=(("fft", "1.000", "5.000", "2.000"),)
        )
        assert _table_lines(rows, tmp_path) == table.markdown_lines()

    def test_a_variant_holding_no_sound_of_a_category_reads_nan_there(self, tmp_path: Path) -> None:
        rows = [
            _row("fft", "tone-a", "tones", 1.0),
            _row("fft", "hiss", "noise", 3.0),
            _row("cqt", "tone-a", "tones", 2.0),
        ]

        table = Table(
            columns=(VARIANT_COLUMN, "tones", "noise", MEAN_COLUMN),
            rows=(("fft", "1.000", "3.000", "2.000"), ("cqt", "2.000", "nan", "2.000")),
        )
        assert _table_lines(rows, tmp_path) == table.markdown_lines()

    def test_no_row_leaves_the_title_alone(self, tmp_path: Path) -> None:
        path = tmp_path / "report.md"

        write_markdown([], path)

        assert path.read_text(encoding="utf-8") == f"{REPORT_TITLE}\n"
