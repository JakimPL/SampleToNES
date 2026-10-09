import csv
from pathlib import Path
from typing import Final, List, Self, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, model_validator

MARKDOWN_RULE: Final[str] = "---"
MARKDOWN_SEPARATOR: Final[str] = " | "


class Table(BaseModel):
    """A report's table: a header and rows of cells already written as text.

    A report builds a table once and writes it both ways, as CSV another tool reads and as the
    lines of a Markdown document a person reads, so the two copies carry the same cells.

    Attributes:
        columns: The header row.
        rows: The rows, each with one cell per column.
    """

    model_config = ConfigDict(frozen=True)

    columns: Tuple[str, ...]
    rows: Tuple[Tuple[str, ...], ...]

    @model_validator(mode="after")
    def _rows_fill_the_columns(self) -> Self:
        """Raises:
        ValueError: If a row holds a different number of cells than there are columns.
        """
        for index, row in enumerate(self.rows):
            if len(row) != len(self.columns):
                raise ValueError(f"Row {index} holds {len(row)} cells for {len(self.columns)} columns.")

        return self

    def write_csv(self, path: Path) -> None:
        """Writes the table as UTF-8 CSV, the header first.

        Args:
            path: Where the table is written.
        """
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(self.columns)
            writer.writerows(self.rows)

    def markdown_lines(self) -> List[str]:
        """The table as the lines of a Markdown document: the header, the rule and one line per row."""
        return [
            self._markdown_line(self.columns),
            "|" + "|".join(MARKDOWN_RULE for _ in self.columns) + "|",
            *(self._markdown_line(row) for row in self.rows),
        ]

    @staticmethod
    def _markdown_line(cells: Sequence[str]) -> str:
        return f"| {MARKDOWN_SEPARATOR.join(cells)} |"
