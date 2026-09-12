import csv
from pathlib import Path
from typing import List, Sequence


def write_csv(
    path: Path,
    columns: Sequence[str],
    rows: Sequence[Sequence[str]],
) -> None:
    """Writes a table another tool reads.

    Args:
        path: Where the table is written.
        columns: The header row.
        rows: The rows, each as its cells.
    """
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)


def markdown_table(
    columns: Sequence[str],
    rows: Sequence[Sequence[str]],
) -> List[str]:
    """A table a reader reads, as the lines of a markdown document.

    Args:
        columns: The header row.
        rows: The rows, each as its cells.

    Returns:
        List[str]: The header, the rule and one line per row.
    """
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines
