import json
import os
from pathlib import Path
from statistics import median
from typing import Dict, Final, List, Sequence

from automation.environment import ARTIFACTS_VARIABLE

LONG_GAP_SECONDS: Final[float] = 0.1


def frame_readings(stamps: List[float], last_gesture: float) -> Dict[str, float]:
    """What the clock said after every frame, read as the gaps between frames and the frames a second.

    Args:
        stamps: The clock after each frame drawn, in order.
        last_gesture: The clock at the last gesture, which the drain after it is measured from.
    """
    gaps = [later - earlier for earlier, later in zip(stamps, stamps[1:])]
    span = stamps[-1] - stamps[0]
    return {
        "frames": len(stamps),
        "seconds": span,
        "longest_gap_seconds": max(gaps),
        "median_gap_seconds": median(gaps),
        "gaps_over_a_tenth": sum(1 for gap in gaps if gap > LONG_GAP_SECONDS),
        "frames_per_second": (len(stamps) - 1) / span,
        "drain_seconds_after_the_last_release": stamps[-1] - last_gesture,
    }


def longest_gap_after_each(stamps: List[float], gestures: Sequence[float]) -> List[float]:
    """The longest gap between two frames after each gesture and before the next, one reading per gesture."""
    readings: List[float] = []
    bounds = [*gestures, float("inf")]
    for started, ended in zip(bounds, bounds[1:]):
        window = [stamp for stamp in stamps if started <= stamp < ended]
        gaps = [later - earlier for earlier, later in zip(window, window[1:])]
        readings.append(max(gaps, default=0.0))

    return readings


def keep_readings(name: str, readings: Dict[str, object]) -> None:
    """Prints the readings and keeps them beside the scenario's other files."""
    print(json.dumps(readings))
    (Path(os.environ[ARTIFACTS_VARIABLE]) / name).write_text(json.dumps(readings, indent=2))
