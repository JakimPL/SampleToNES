from collections import deque
from time import monotonic
from typing import Deque, Final, Optional, Tuple

ESTIMATION_MEASUREMENTS_SAMPLES: Final[float] = 0.05


class ETAEstimator:
    def __init__(
        self,
        total: int,
        ems: float = ESTIMATION_MEASUREMENTS_SAMPLES,
    ) -> None:
        self._total = total
        self._ems = self._get_estimation_measurements_samples(ems)
        self._samples_window: Deque[Tuple[float, int]] = deque(maxlen=self._ems)
        self._processed_items: int = 0

    def update(self, completed_items: int) -> Optional[float]:
        now = monotonic()
        self._processed_items = completed_items
        self._samples_window.append((now, completed_items))

        if completed_items >= self._total:
            return 0.0
        if len(self._samples_window) < 2:
            return None

        return self._estimate_remaining_seconds(completed_items, now)

    @classmethod
    def format_duration(cls, seconds: Optional[float]) -> str:
        if seconds is None:
            return "?"
        if seconds <= 0:
            return "0s"

        secs = int(seconds)
        if secs <= 0:
            return "0s"

        minutes, seconds_remaining = divmod(secs, 60)
        hours, minutes = divmod(minutes, 60)

        if hours:
            return f"{hours}h {minutes:02d}m {seconds_remaining:02d}s"
        if minutes:
            return f"{minutes}m {seconds_remaining:02d}s"

        return f"{seconds_remaining}s"

    def _get_estimation_measurements_samples(self, ems: float) -> int:
        if isinstance(ems, float):
            ems = round(ems * self._total)

        return max(3, int(ems))

    def _estimate_remaining_seconds(
        self,
        completed_items: int,
        current_time: float,
    ) -> Optional[float]:
        if completed_items >= self._total:
            return 0.0
        if len(self._samples_window) < 2:
            return None

        first_time, first_completed = self._samples_window[0]
        delta_completed = completed_items - first_completed
        delta_time = current_time - first_time

        if delta_time <= 0 or delta_completed <= 0:
            return None

        rate = delta_completed / delta_time
        remaining = self._total - completed_items
        return remaining / rate
