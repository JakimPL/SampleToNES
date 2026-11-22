from pathlib import Path
from typing import Callable, Dict, Final, List, Sequence, Tuple

import numpy as np

from sampletones_shared.utils.tables import Table
from sampletones_tools.calibration.referee.protocol import SCORE_READING
from sampletones_tools.calibration.rows import CalibrationRow

VARIANT_COLUMN: Final[str] = "variant"
CSV_COLUMNS: Final[Tuple[str, ...]] = (
    VARIANT_COLUMN,
    "item",
    "family",
    "category",
    "referee",
    "component",
    "score",
)
MEAN_COLUMN: Final[str] = "mean"
REPORT_TITLE: Final[str] = "# Calibration report"
CSV_SCORE_FORMAT: Final[str] = ".6f"
MEAN_FORMAT: Final[str] = ".3f"
MISSING_MEAN: Final[float] = float("nan")

RowKey = Callable[[CalibrationRow], str]


def write_csv(rows: List[CalibrationRow], path: Path) -> None:
    """
    Write every calibration row as CSV.

    Args:
        rows: Scored rows from the runner.
        path: Target CSV path.
    """
    Table(columns=CSV_COLUMNS, rows=tuple(_csv_cells(row) for row in rows)).write_csv(path)


def write_markdown(rows: List[CalibrationRow], path: Path) -> None:
    """
    Write a section per family, and in it a per-referee pivot of mean scores: one row per variant,
    one column per category of the family, with the family's mean last. Lower scores mean closer
    reconstructions.

    Families stand apart, each read on its own terms, so a mean spans one family alone. Each
    referee's score leads its subsection, and every further reading it reports follows in a table of
    its own. Families, referees, readings, categories and variants each follow the order the rows
    first name them in, which is the run's order.

    Args:
        rows: Scored rows from the runner.
        path: Target markdown path.
    """
    lines: List[str] = [REPORT_TITLE, ""]
    for family, family_rows in _grouped(rows, lambda row: row.family).items():
        lines.extend((f"## {family}", ""))
        for referee, referee_rows in _grouped(family_rows, lambda row: row.referee).items():
            lines.extend((f"### {referee}", ""))
            for component, component_rows in _grouped(referee_rows, lambda row: row.component).items():
                if component != SCORE_READING:
                    lines.extend((f"#### {component}", ""))

                lines.extend((*_pivot_table(component_rows).markdown_lines(), ""))

    path.write_text("\n".join(lines), encoding="utf-8")


def _csv_cells(row: CalibrationRow) -> Tuple[str, ...]:
    """A row's cells under ``CSV_COLUMNS``."""
    return (
        row.variant,
        row.item,
        row.family,
        row.category,
        row.referee,
        row.component,
        format(row.score, CSV_SCORE_FORMAT),
    )


def _pivot_table(rows: List[CalibrationRow]) -> Table:
    """One reading's table: a row per variant, a column per category, and the variant's mean last."""
    categories = list(_grouped(rows, lambda row: row.category))
    variants = _grouped(rows, lambda row: row.variant)
    cells = [_pivot_row(variant, variant_rows, categories) for variant, variant_rows in variants.items()]
    return Table(columns=(VARIANT_COLUMN, *categories, MEAN_COLUMN), rows=tuple(cells))


def _pivot_row(variant: str, rows: List[CalibrationRow], categories: Sequence[str]) -> Tuple[str, ...]:
    """A variant's means: one per category, ``MISSING_MEAN`` where it holds none, then its mean over every sound.

    The last mean weighs every sound alike, so a category of many sounds weighs in it as much as it
    holds sounds.
    """
    by_category = _grouped(rows, lambda row: row.category)
    means = {category: _mean(category_rows) for category, category_rows in by_category.items()}
    scores = [format(means.get(category, MISSING_MEAN), MEAN_FORMAT) for category in categories]
    return (variant, *scores, format(_mean(rows), MEAN_FORMAT))


def _mean(rows: List[CalibrationRow]) -> float:
    """The mean of the rows' scores, taken in their order."""
    return float(np.mean([row.score for row in rows]))


def _grouped(rows: Sequence[CalibrationRow], key: RowKey) -> Dict[str, List[CalibrationRow]]:
    """The rows by ``key``, the groups in the order the rows first name them, each group's rows in order."""
    groups: Dict[str, List[CalibrationRow]] = {}
    for row in rows:
        groups.setdefault(key(row), []).append(row)

    return groups
