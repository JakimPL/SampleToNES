from collections import defaultdict
from pathlib import Path
from typing import Dict, Final, Iterable, List, Tuple

import numpy as np

from sampletones_shared.utils.tables import Table
from sampletones_tools.calibration.referee.protocol import SCORE_READING
from sampletones_tools.calibration.runner import CalibrationRow

VARIANT_COLUMN: Final[str] = "variant"
CSV_COLUMNS: Final[Tuple[str, ...]] = (VARIANT_COLUMN, "item", "category", "referee", "component", "score")
OVERALL_COLUMN: Final[str] = "overall"


def write_csv(rows: List[CalibrationRow], path: Path) -> None:
    """
    Write every calibration row as CSV.

    Args:
        rows: Scored rows from the runner.
        path: Target CSV path.
    """
    Table(
        columns=CSV_COLUMNS,
        rows=tuple(
            (row.variant, row.item, row.category, row.referee, row.component, f"{row.score:.6f}") for row in rows
        ),
    ).write_csv(path)


def write_markdown(rows: List[CalibrationRow], path: Path) -> None:
    """
    Write a per-referee pivot of mean scores: one row per variant, one column per
    category, with the overall mean last. Lower scores mean closer reconstructions.

    Each referee's score leads its section, and every further reading it reports follows
    in a table of its own.

    Args:
        rows: Scored rows from the runner.
        path: Target markdown path.
    """
    lines: List[str] = ["# Calibration report", ""]
    for referee in _ordered(row.referee for row in rows):
        referee_rows = [row for row in rows if row.referee == referee]
        lines.extend((f"## {referee}", ""))
        for component in _ordered(row.component for row in referee_rows):
            component_rows = [row for row in referee_rows if row.component == component]
            if component != SCORE_READING:
                lines.extend((f"### {component}", ""))

            lines.extend((*_pivot_table(component_rows).markdown_lines(), ""))

    path.write_text("\n".join(lines), encoding="utf-8")


def _pivot_table(rows: List[CalibrationRow]) -> Table:
    categories = _ordered(row.category for row in rows)
    means = _mean_scores(rows)
    cells: List[Tuple[str, ...]] = []
    for variant in _ordered(row.variant for row in rows):
        scores = [f"{means.get((variant, category), float('nan')):.3f}" for category in categories]
        overall = np.mean([row.score for row in rows if row.variant == variant])
        cells.append((variant, *scores, f"{float(overall):.3f}"))

    return Table(columns=(VARIANT_COLUMN, *categories, OVERALL_COLUMN), rows=tuple(cells))


def _mean_scores(rows: List[CalibrationRow]) -> Dict[Tuple[str, str], float]:
    scores: Dict[Tuple[str, str], List[float]] = defaultdict(list)
    for row in rows:
        scores[(row.variant, row.category)].append(row.score)

    return {key: float(np.mean(values)) for key, values in scores.items()}


def _ordered(values: Iterable[str]) -> List[str]:
    seen: List[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)

    return seen
