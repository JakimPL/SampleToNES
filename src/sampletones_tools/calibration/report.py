import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np

from .runner import CalibrationRow


def write_csv(rows: List[CalibrationRow], path: Path) -> None:
    """
    Write every calibration row as CSV.

    Args:
        rows: Scored rows from the runner.
        path: Target CSV path.
    """
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["variant", "item", "category", "referee", "score"])
        for row in rows:
            writer.writerow([row.variant, row.item, row.category, row.referee, f"{row.score:.6f}"])


def write_markdown(rows: List[CalibrationRow], path: Path) -> None:
    """
    Write a per-referee pivot of mean scores: one row per variant, one column per
    category, with the overall mean last. Lower scores mean closer reconstructions.

    Args:
        rows: Scored rows from the runner.
        path: Target markdown path.
    """
    lines: List[str] = ["# Calibration report", ""]

    for referee in _ordered(row.referee for row in rows):
        referee_rows = [row for row in rows if row.referee == referee]
        categories = _ordered(row.category for row in referee_rows)
        variants = _ordered(row.variant for row in referee_rows)
        means = _mean_scores(referee_rows)

        lines.append(f"## {referee}")
        lines.append("")
        lines.append("| variant | " + " | ".join(categories) + " | overall |")
        lines.append("|---" * (len(categories) + 2) + "|")
        for variant in variants:
            cells = [f"{means.get((variant, category), float('nan')):.3f}" for category in categories]
            overall = np.mean([row.score for row in referee_rows if row.variant == variant])
            lines.append(f"| {variant} | " + " | ".join(cells) + f" | {float(overall):.3f} |")

        lines.append("")

    path.write_text("\n".join(lines))


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
