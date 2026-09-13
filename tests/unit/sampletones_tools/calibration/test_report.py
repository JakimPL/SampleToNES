import csv
from pathlib import Path
from typing import Final, List

from sampletones_shared.utils.tables import Table
from sampletones_tools.calibration.report import CSV_COLUMNS, OVERALL_COLUMN, VARIANT_COLUMN, write_csv, write_markdown
from sampletones_tools.calibration.runner import CalibrationRow

ROWS: Final[List[CalibrationRow]] = [
    CalibrationRow(variant="fft", item="tone-a", category="tones", referee="spectral", score=0.25),
    CalibrationRow(variant="fft", item="tone-b", category="tones", referee="spectral", score=0.75),
    CalibrationRow(variant="fft", item="hiss", category="noise", referee="spectral", score=1.0),
    CalibrationRow(variant="cqt", item="tone-a", category="tones", referee="spectral", score=0.5),
    CalibrationRow(variant="cqt", item="hiss", category="noise", referee="spectral", score=0.5),
    CalibrationRow(variant="fft", item="tone-a", category="tones", referee="envelope", score=2.0),
]


class TestWriteCsv:
    def test_every_row_reads_back_under_the_columns(self, tmp_path: Path) -> None:
        path = tmp_path / "report.csv"

        write_csv(ROWS, path)

        with path.open(newline="", encoding="utf-8") as handle:
            header, *cells = list(csv.reader(handle))
        assert tuple(header) == CSV_COLUMNS
        assert [(row[0], row[1], row[2], row[3], float(row[4])) for row in cells] == [
            (row.variant, row.item, row.category, row.referee, row.score) for row in ROWS
        ]


class TestWriteMarkdown:
    def test_each_referee_pivots_the_mean_of_every_variant_by_category(self, tmp_path: Path) -> None:
        path = tmp_path / "report.md"

        write_markdown(ROWS, path)

        lines = path.read_text(encoding="utf-8").split("\n")
        spectral = Table(
            columns=(VARIANT_COLUMN, "tones", "noise", OVERALL_COLUMN),
            rows=(("fft", "0.500", "1.000", "0.667"), ("cqt", "0.500", "0.500", "0.500")),
        )
        envelope = Table(columns=(VARIANT_COLUMN, "tones", OVERALL_COLUMN), rows=(("fft", "2.000", "2.000"),))
        assert lines == [
            "# Calibration report",
            "",
            "## spectral",
            "",
            *spectral.markdown_lines(),
            "",
            "## envelope",
            "",
            *envelope.markdown_lines(),
            "",
        ]
