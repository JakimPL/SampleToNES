import csv
from pathlib import Path
from typing import Final, List

from sampletones_shared.utils.tables import Table
from sampletones_tools.calibration.report import CSV_COLUMNS, MEAN_COLUMN, VARIANT_COLUMN, write_csv, write_markdown
from sampletones_tools.calibration.runner import CalibrationRow

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
            "# Calibration report",
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
