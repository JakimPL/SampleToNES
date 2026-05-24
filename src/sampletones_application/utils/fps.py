from typing import Optional

from ..constants.main import VAL_FPS_TIME_INTERVAL


class FPSTimer:
    def __init__(self, interval: float = VAL_FPS_TIME_INTERVAL) -> None:
        self._interval: float = interval
        self.fps_timer: float = interval
        self.fps_delta: float = 0.0
        self.fps_count: int = 0
        self.total_delta: float = 0.0
        self._fps: Optional[float] = None

    def add(self, delta_time: float) -> None:
        self.fps_timer -= delta_time
        self.fps_delta += delta_time
        self.fps_count += 1

    def calculate(self, delta_time: float) -> None:
        if self.fps_count > 0:
            self.total_delta = self.fps_delta / self.fps_count
        else:
            self.total_delta = delta_time

        self._fps = 1.0 / self.total_delta if self.total_delta > 0.0 else 0.0
        self.reset()

    def reset(self) -> None:
        self.fps_timer = self._interval
        self.fps_delta = 0.0
        self.fps_count = 0

    def update(self, delta_time: float) -> float:
        if self.fps_timer > 0.0:
            self.add(delta_time)
        else:
            self.calculate(delta_time)

        return self.fps

    @property
    def fps(self) -> float:
        return self._fps if self._fps is not None else 0.0
