import math
from dataclasses import dataclass
from typing import Dict, Final, List, Optional

from .referee.protocol import SCORE_READING
from .renders import RenderRecord

LOG_GAP: Final[str] = "log-gap"


@dataclass(frozen=True)
class CalibrationRow:
    """One reading of one conversion, as the reports hold it.

    Attributes:
        variant: The label of the variant converted under.
        item: The sound converted.
        family: The sound's family, which the markdown report sections by.
        category: The sound's category, which the markdown report pivots on.
        referee: The referee that took the reading.
        component: The reading's name, ``SCORE_READING`` for the referee's score.
        score: The reading.
    """

    variant: str
    item: str
    family: str
    category: str
    referee: str
    component: str
    score: float


def recorded_rows(record: RenderRecord) -> List[CalibrationRow]:
    """The rows a record holds, one per (referee, reading), in the order the record keeps them.

    A fresh conversion and a resumed run both read their rows through here, so a run reports a
    conversion alike whether it made it or read its record back.
    """
    rows: List[CalibrationRow] = []
    for referee, readings in _readings(record).items():
        for component, value in readings.items():
            rows.append(
                CalibrationRow(
                    variant=record.variant,
                    item=record.item,
                    family=record.family,
                    category=record.category,
                    referee=referee,
                    component=component,
                    score=value,
                )
            )

    return rows


def log_gap(score: float, silence: float) -> Optional[float]:
    """How far a render stands from its recording against silence: the natural logarithm of score over silence.

    A mean of log gaps is the gap a family closes in ratio, so a few sounds far past silence weigh in
    it as much as they differ in kind. Zero is as close as silence, below zero closer.

    Returns:
        The log gap, or ``None`` where the score or silence's score is zero or below, which no
        logarithm reads.
    """
    if score > 0.0 and silence > 0.0:
        return math.log(score / silence)

    return None


def _readings(record: RenderRecord) -> Dict[str, Dict[str, float]]:
    """Every referee's readings in the record, each audio referee's log gap following its own readings."""
    readings = {referee: dict(values) for referee, values in record.judgments.items()}
    for referee, silence in record.silence.items():
        score = readings.get(referee, {}).get(SCORE_READING)
        gap = log_gap(score, silence) if score is not None else None
        if gap is not None:
            readings[referee][LOG_GAP] = gap

    return readings
