import csv
from pathlib import Path

import pytest

from sampletones_shared.utils.tables import Table


@pytest.fixture(name="table")
def table_fixture() -> Table:
    return Table(
        columns=("song", "bytes"),
        rows=(("Theme, reprise", "120"), ("Café", "7")),
    )


class TestTable:
    def test_the_csv_reads_back_cell_for_cell(self, table: Table, tmp_path: Path) -> None:
        path = tmp_path / "report.csv"

        table.write_csv(path)

        with path.open(encoding="utf-8", newline="") as handle:
            assert [tuple(row) for row in csv.reader(handle)] == [table.columns, *table.rows]

    def test_the_markdown_is_the_header_the_rule_and_a_line_per_row(self, table: Table) -> None:
        assert table.markdown_lines() == [
            "| song | bytes |",
            "|---|---|",
            "| Theme, reprise | 120 |",
            "| Café | 7 |",
        ]

    def test_a_table_without_rows_is_its_header_and_rule(self) -> None:
        assert Table(columns=("song",), rows=()).markdown_lines() == ["| song |", "|---|"]

    def test_a_row_short_of_the_columns_is_refused(self) -> None:
        with pytest.raises(ValueError, match="Row 1 holds 1 cells for 2 columns"):
            Table(columns=("song", "bytes"), rows=(("one", "1"), ("two",)))
