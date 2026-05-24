from collections import deque
from time import monotonic
from typing import Deque, Optional, Tuple, Union

ESTIMATION_MEASUREMENTS_SAMPLES = 0.05


class ETAEstimator:
    def __init__(self, total: int, ems: Union[float, int] = ESTIMATION_MEASUREMENTS_SAMPLES) -> None:
        self._total = total
        self._ems = self._get_estimation_measurements_samples(ems)
        self._samples_window: Deque[Tuple[float, int]] = deque(maxlen=self._ems)
        self._processed_items: int = 0

    def update(self, completed_items: int) -> str:
        now = monotonic()
        self._processed_items = completed_items
        self._samples_window.append((now, completed_items))

        if completed_items >= self._total:
            return "0s"
        if len(self._samples_window) < 2:
            return "?"

        eta_seconds = self._estimate_remaining_seconds(completed_items, now)
        if eta_seconds is None:
            return "?"
        if eta_seconds <= 0:
            return "0s"

        return self._format_duration(eta_seconds)

    def get_percent_string(self) -> str:
        if self._total == 0:
            return "100%"

        percent = int(self._processed_items * 100 / self._total)
        percent = max(0, min(100, percent))
        return f"{percent}%"

    def _get_estimation_measurements_samples(self, ems: Union[float, int]) -> int:
        if isinstance(ems, float):
            ems = round(ems * self._total)

        return max(3, int(ems))

    def _estimate_remaining_seconds(self, completed_items: int, current_time: float) -> Optional[float]:
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

    def _format_duration(self, seconds: float) -> str:
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
